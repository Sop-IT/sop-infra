from setuptools import setup, find_packages


setup(
    name="sop-infra",
    version="0.5.7",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'phonenumbers',
        'sop-utils'
    ],
    description="Manage infrastructure informations of each site.",
    author="Soprema NOC team",
    author_email="noc@soprema.com",
    classifiers=[
        "Framework :: Django",
        "Programming Language :: Python :: 3",
    ],
    zip_safe=False,
)
