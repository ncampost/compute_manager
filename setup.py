from setuptools import setup

setup(
    name='compute_manager',
    version='0.1',
    py_modules=['compute_manager'],
    install_requires=[
        'Click',
        'google-api-python-client',
        'PyYAML',
        'environs',
    ],
    entry_points='''
        [console_scripts]
        compute_manager=compute_manager:compute_manager
    '''
)