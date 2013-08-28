from setuptools import setup, find_packages

setup(
    name="codetree",
    version="0.0.1",
    description="A code tree builder",
    author="Matthew Wedgwood",
    author_email="matthew.wedgwood@ubuntu.com",
    url="http://github.com/slank/codetree",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Programming Language :: Python",
        "License :: OSI Approved :: MIT License",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Intended Audience :: Developers"],
#    test_suite="tests",
    entry_points={
        "console_scripts": ['codetree = codetree.cli:main']},
    include_package_data=False,
)
