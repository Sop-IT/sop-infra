from setuptools import setup, find_packages


setup(
    name='sop-infra',
    version='1.0.3',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'sop-utils>=1.0.7',
    ],
    description = "Manage infrastructure informations of each site.",
    author="Leorevoir",
    author_email="leo.quinzler@epitech.eu",
    classifiers=[
        'Framework :: Django',
        'Programming Language :: Python :: 3',
    ],
    zip_safe=False,
)
