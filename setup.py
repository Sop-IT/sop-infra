from setuptools import setup, find_packages


setup(
    name="sop-infra",
    version="0.4.37",
    packages=find_packages(),
    include_package_data=True,
    description="Manage infrastructure informations of each site.",
    author="Soprema NOC team",
    author_email="noc@soprema.com",
    classifiers=[
        "Framework :: Django",
        "Programming Language :: Python :: 3",
    ],
    zip_safe=False,
)
