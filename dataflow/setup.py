# -*- coding: utf-8 -*-
"""Setup file para o Pipeline do Apache Beam."""
import setuptools

setuptools.setup(
    name='harry_potter_spanner_ingestion',
    version='1.0.0',
    install_requires=[
        'apache-beam[gcp]==2.53.0', # Versão compatível
        'google-cloud-spanner>=3.59.0',
        'google-cloud-aiplatform>=1.128.0',
        # Inclua outras bibliotecas que você precisa para transformação de dados
    ],
    packages=setuptools.find_packages(),
)
