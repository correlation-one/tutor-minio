from __future__ import annotations

import os
from glob import glob
from typing import Literal

import pkg_resources

from tutor import hooks as tutor_hooks

from .__about__ import __version__

HERE = os.path.abspath(os.path.dirname(__file__))


tutor_hooks.Filters.CONFIG_DEFAULTS.add_items(
    [
        ("MINIO_VERSION", __version__),
        ("MINIO_BUCKET_NAME", "openedx"),
        ("MINIO_FILE_UPLOAD_BUCKET_NAME", "openedxuploads"),
        ("MINIO_VIDEO_UPLOAD_BUCKET_NAME", "openedxvideos"),
        ("MINIO_HOST", "files.{{ LMS_HOST }}"),
        ("MINIO_CONSOLE_HOST", "minio.{{ LMS_HOST }}"),
        # https://hub.docker.com/r/minio/minio/tags
        # https://hub.docker.com/r/minio/mc/tags
        # We must stick to these older releases because they are the last ones that support gateway mode to Azure:
        # https://blog.min.io/deprecation-of-the-minio-gateway/
        # https://min.io/docs/minio/linux/operations/install-deploy-manage/migrate-fs-gateway.html
        (
            "MINIO_DOCKER_IMAGE",
            "docker.io/minio/minio:RELEASE.2022-03-26T06-49-28Z.hotfix.26ec6a857",
        ),
        ("MINIO_MC_DOCKER_IMAGE", "docker.io/minio/mc:RELEASE.2022-03-31T04-55-30Z"),
        ("MINIO_GATEWAY", None),
        ("MINIO_GCS_APPLICATION_CREDENTIALS", None),
        ("MINIO_GCS_APPLICATION_ID", None),
        # MINIO_GCS_MULTIPART_THRESHOLD is in bytes. Default is 200MB. This will disable multipart uploads for any
        # upload below that threshold. But it also means that any file larger than the threshold will fail to upload
        # to GCS (including course export/import tar files). Increasing the threshold gives the ability to upload
        # larger files, but with the risk of timeouts, depending on the network speed.
        ("MINIO_GCS_MULTIPART_THRESHOLD", 1024 * 1024 * 200),
    ]
)

tutor_hooks.Filters.CONFIG_UNIQUE.add_items(
    [
        ("MINIO_AWS_SECRET_ACCESS_KEY", "{{ 24|random_string }}"),
    ]
)
tutor_hooks.Filters.CONFIG_OVERRIDES.add_items(
    [
        ("OPENEDX_AWS_ACCESS_KEY", "openedx"),
        ("OPENEDX_AWS_SECRET_ACCESS_KEY", "{{ MINIO_AWS_SECRET_ACCESS_KEY }}"),
    ]
)

@tutor_hooks.Filters.APP_PUBLIC_HOSTS.add()
def add_minio_hosts(
    hosts: list[str], context_name: Literal["local", "dev"]
    ) -> list[str]:
    if context_name == "dev":
        hosts.append("{{ MINIO_CONSOLE_HOST }}:9001")
    else:
        hosts.append("{{ MINIO_CONSOLE_HOST }}")
        
    return hosts

# Add pre-init script as init task with high priority
with open(
    os.path.join(HERE, "templates", "minio", "tasks", "minio", "init.sh"),
    encoding="utf-8",
) as fi:
    tutor_hooks.Filters.CLI_DO_INIT_TASKS.add_item(
        ("minio", fi.read()), priority=tutor_hooks.priorities.HIGH
    )

# Add the "templates" folder as a template root
tutor_hooks.Filters.ENV_TEMPLATE_ROOTS.add_item(
    pkg_resources.resource_filename("tutorminio", "templates")
)
# Render the "build" and "apps" folders
tutor_hooks.Filters.ENV_TEMPLATE_TARGETS.add_items(
    [
        ("minio/build", "plugins"),
        ("minio/apps", "plugins"),
    ],
)
# Load patches from files
for path in glob(
    os.path.join(
        pkg_resources.resource_filename("tutorminio", "patches"),
        "*",
    )
):
    with open(path, encoding="utf-8") as patch_file:
        tutor_hooks.Filters.ENV_PATCHES.add_item(
            (os.path.basename(path), patch_file.read())
        )
