# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


from setuptools import setup, find_packages

name = "rcore"
version = "0.0.1"
description = "Core ROKCT Logic"
author = "RokctAI"
author_email = "admin@rokct.ai"
packages = find_packages()
zip_safe = False
include_package_data = True
install_requires = []

setup(
    name=name,
    version=version,
    description=description,
    author=author,
    author_email=author_email,
    packages=packages,
    zip_safe=zip_safe,
    include_package_data=include_package_data,
    install_requires=install_requires,
)
