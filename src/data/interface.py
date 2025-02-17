"""Module source.py"""

import os

import pandas as pd

import config
import src.data.dictionary
import src.data.encodings
import src.data.filtering
import src.data.source
import src.data.structuring
import src.data.tags
import src.elements.s3_parameters as s3p
import src.elements.service as sr
import src.functions.objects
import src.functions.streams
import src.s3.ingress


class Interface:
    """
    Class Interface

    The steps.
    """

    def __init__(self, service: sr.Service,  s3_parameters: s3p):
        """

        :param service: A suite of services for interacting with Amazon Web Services.
        :param s3_parameters: The overarching S3 parameters settings of this
                              project, e.g., region code name, buckets, etc.
        """

        self.__service: sr.Service = service
        self.__s3_parameters: s3p.S3Parameters = s3_parameters
        self.__configurations = config.Config()

        # The raw data
        self.__raw = src.data.source.Source(s3_parameters=s3_parameters).exc()

        # Instances
        self.__dictionary = src.data.dictionary.Dictionary()
        self.__objects = src.functions.objects.Objects()
        self.__streams = src.functions.streams.Streams()

    def __tags(self):
        """

        :return:
        """

        tags = src.data.tags.Tags(data=self.__raw).exc()
        enumerator, archetype = src.data.encodings.Encodings().exc(tags=tags)

        return tags, enumerator, archetype

    def __data(self, tags: pd.DataFrame, enumerator: dict) -> pd.DataFrame:
        """
        Filtering out instances of the raw data that are associated with elements/tags
        that have fewer than an expected number of occurrences.

        :param tags:
        :param enumerator:
        :return:
        """

        filtering = src.data.filtering.Filtering()
        filtered = filtering(data=self.__raw, tags=tags)

        data = src.data.structuring.Structuring(data=filtered, enumerator=enumerator).exc()

        return data

    def exc(self) -> list[str]:
        """

        :return:
        """

        # Foremost (a) the table of viable tags, and (b) an enumeration of the tags; archetype
        # is the inverse of enumerator.
        tags: pd.DataFrame
        enumerator: dict
        archetype: dict
        tags, enumerator, archetype = self.__tags()

        # Tha data; only the instances associated with viable tags
        data = self.__data(tags=tags, enumerator=enumerator)

        pre = os.path.join(self.__configurations.prepared_, '{}')
        self.__objects.write(nodes=enumerator, path=pre.format('enumerator.json'))
        self.__objects.write(nodes=archetype, path=pre.format('archetype.json'))
        self.__streams.write(blob=data, path=pre.format('data.csv'))

        # Inventory of data files
        strings = self.__dictionary.exc(
            path=self.__configurations.warehouse, extension='*', prefix=self.__s3_parameters.path_internal_data)

        # Transfer
        messages = src.s3.ingress.Ingress(
            service=self.__service, bucket_name=self.__s3_parameters.internal).exc(strings=strings)

        return messages
