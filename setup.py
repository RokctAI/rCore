# Copyright (c) 2026 ROKCT INTELLIGENCE (PTY) LTD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# Copyright (c) 2026, Rokct Intelligence (pty) Ltd.
# For license information, please see license.txt


from setuptools import setup, find_packages

name = "rcore"
version = "1.4.9"
description = "Core ROKCT Logic"
author = "ROKCT INTELLIGENCE (PTY) LTD"
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
