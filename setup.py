from setuptools import setup, find_packages
setup(
    name="GJEMSRDViewer",
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    packages=find_packages(exclude=["^\."]),
    exclude_package_data={'': ["Readme.md"]},
    install_requires=["nixio==1.4.2",
                      "numpy==1.11.3",
                      "PyInstaller==3.3.1",
                      "pyqt==4.11",
                      "neo==0.5",
                      "matplotlib==1.5",
                      ],

    python_requires="==2.7",
    )