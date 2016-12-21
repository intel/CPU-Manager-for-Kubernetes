from setuptools import setup

setup(name='kcm',
      version='0.1.0',
      description='Support minimal comms use cases on Kubernetes',
      url='http://github.com/intelsdi-x/kubernetes-comms-mvp',
      author='Intel SDI-E',
      author_email='',
      license='',
      packages=['intel'],
      install_requires=[
          'docopt>=0.6, <1.0',
      ],
      zip_safe=False)
