from setuptools import setup, find_packages

setup(
    name="lukhed_x",
    version="0.1.1",
    description="Custom tweepy wrapper for posting on X. Used by @grindSunday and @popPunkpoets Bots",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="lukhed",
    author_email="lukhed.mail@gmail.com",
    url="https://github.com/lukhed/lukhed_x",
    packages=find_packages(),
    include_package_data=True,  # Ensures MANIFEST.in is used
    python_requires=">=3.9",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "lukhed-basic-utils>=1.6.4",
        "tweepy>=4.16.0",
    ],
)