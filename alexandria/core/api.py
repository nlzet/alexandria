import logging
from os.path import splitext
from typing import Optional, Tuple

from django.conf import settings
from django.core.files import File
from django.utils.translation import gettext

from alexandria.core import models, presign_urls
from alexandria.core.validations import validate_file

log = logging.getLogger(__name__)


def make_signature_components(
    pk: str,
    hostname: str,
    expires: Optional[int] = None,
    scheme: str = "http",
    download_path: Optional[str] = None,
) -> Tuple[str, int, str]:
    return presign_urls.make_signature_components(
        pk, hostname, expires, scheme, download_path
    )


def verify_signed_components(
    pk: str,
    hostname: str,
    token_sig: str,
    expires: Optional[int] = None,
    scheme: str = "http",
    download_path: Optional[str] = None,
):
    return presign_urls.verify_signed_components(
        pk, hostname, token_sig, expires, scheme, download_path
    )


def copy_document(
    document: models.Document, user: str, group: str, category: models.Category
):
    """
    Copy a document and all its original files to a new document.

    This function eases the copying of documents by automatically setting important fields.
    Uses `create_file` to copy the original document files.
    """

    basename, ext = splitext(document.title)
    document_title = gettext("{basename} (copy){ext}").format(
        basename=basename, ext=ext
    )
    new_document = models.Document.objects.create(
        title=document_title,
        description=document.description,
        metainfo=document.metainfo,
        category=category,
        created_by_user=user,
        created_by_group=group,
        modified_by_user=user,
        modified_by_group=group,
    )

    # Copying only the originals - create_file() will create the thumbnails
    document_files = models.File.objects.filter(
        document=document, variant=models.File.Variant.ORIGINAL.value
    ).order_by("created_at")
    new_files = []
    for document_file in document_files:
        new_files.append(
            create_file(
                name=document_file.name,
                document=new_document,
                content=document_file.content,
                mime_type=document_file.mime_type,
                size=document_file.size,
                user=document_file.created_by_user,
                group=document_file.created_by_group,
                metainfo=document_file.metainfo,
            )
        )

    return new_document


def create_document_file(
    user: str,
    group: str,
    category: models.Category,
    document_title: str,
    file_name: str,
    file_content: File,
    mime_type: str,
    file_size: int,
    additional_document_attributes={},
    additional_file_attributes={},
):
    """
    Create a document and file with the given attributes.

    This function eases the creation of documents and files by automatically setting important fields.
    Uses `create_file` to create the file.
    """
    document = models.Document.objects.create(
        title=document_title,
        category=category,
        created_by_user=user,
        created_by_group=group,
        modified_by_user=user,
        modified_by_group=group,
        **additional_document_attributes,
    )
    file = create_file(
        document=document,
        user=user,
        group=group,
        name=file_name,
        content=file_content,
        mime_type=mime_type,
        size=file_size,
        **additional_file_attributes,
    )

    return document, file


def create_file(
    document: models.Document,
    user: str,
    group: str,
    name: str,
    content: File,
    mime_type: str,
    size: int,
    **additional_attributes,
):
    """
    Create a file with defaults and generate a thumbnail.

    Use this instead of the normal File.objects.create to ensure that all important fields are set.
    As well as generating a thumbnail for the file.
    """
    file = models.File(
        name=name,
        content=content,
        mime_type=mime_type,
        size=size,
        document=document,
        encryption_status=(
            settings.ALEXANDRIA_ENCRYPTION_METHOD
            if settings.ALEXANDRIA_ENABLE_AT_REST_ENCRYPTION
            else None
        ),
        created_by_user=user,
        created_by_group=group,
        modified_by_user=user,
        modified_by_group=group,
        **additional_attributes,
    )
    validate_file(file)
    file.save()

    return file
