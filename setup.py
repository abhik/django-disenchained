from setuptools import setup


setup(
    name='django-disenchained',
    version='0.8',
    description='django-disenchained: free Django from the shackles of inefficient queries!',

    author='Abhik Shah',
    author_email='abhik@counsyl.com',
    url='http://github.com/abhik/django-disenchained',
    license='BSD',

    packages=['disenchained'],
    install_requires=['django-debug-toolbar>=0.9.4'],

    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules']
    )
