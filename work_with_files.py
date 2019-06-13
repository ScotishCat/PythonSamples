import json
import os
from datetime import datetime
from random import choice, randint
from string import ascii_letters, digits
from xml.etree import ElementTree as ET


class InvalidTypeError(Exception):
    message = 'Invalid type.'


class InvalidSequenceLength(Exception):
    message = 'Too many items in the sequence.'


class InvalidValueError(Exception):
    message = 'Invalid value.'


class FibonacciError(Exception):
    message = 'Data structure may change elements order.'


JSON_PATH = 'data.json'
XML_PATH = 'data.xml'
TIME_FORMAT = '%d.%m.%Y %H:%M'


class Serializer:
    @staticmethod
    def _validate_data(data):
        raise NotImplementedError

    @staticmethod
    def encode(sequence, s_type, seq_type, cr_time, author, min_el, max_el):
        raise NotImplementedError

    def decode(self, path):
        raise NotImplementedError


class XMLSerializer(Serializer):
    @staticmethod
    def _validate_data(data):
        root = data.getroot()
        if (
                root.find('./sequence') and
                root.find('./metadata') and
                root.find('./metadata/type').text and
                root.find('./metadata/seq_type').text and
                root.find('./metadata/len').text and
                root.find('./metadata/el_type').text and
                root.find('./metadata/max').text and
                root.find('./metadata/date_created').text and
                root.find('./metadata/date_modified').text and
                root.find('./metadata/author').text
        ):
            return True
        return False

    @staticmethod
    def encode(sequence, s_type, seq_type, cr_time, author, min_el, max_el):
        mod_date = datetime.today().strftime(TIME_FORMAT)
        root = ET.Element('data')
        xml_sequence = ET.SubElement(root, 'sequence')
        for i in sequence:
            if isinstance(sequence, dict):
                ET.SubElement(xml_sequence, 'el', key=f'{i}').text = str(i)
            else:
                ET.SubElement(xml_sequence, 'el').text = str(i)

        xml_meta = ET.SubElement(root, 'metadata')
        ET.SubElement(xml_meta, 'type').text = s_type
        ET.SubElement(xml_meta, 'seq_type').text = seq_type
        ET.SubElement(xml_meta, 'len').text = str(len(sequence))
        ET.SubElement(xml_meta, 'el_type').text = 'int'
        ET.SubElement(xml_meta, 'date_created').text = cr_time
        ET.SubElement(xml_meta, 'date_modified').text = mod_date
        ET.SubElement(xml_meta, 'author').text = author
        ET.SubElement(xml_meta, 'min').text = str(min_el)
        ET.SubElement(xml_meta, 'max').text = str(max_el)

        return ET.tostring(root, encoding='utf8').decode('utf8')

    def decode(self, path):
        try:
            tree = ET.parse(path)
        except ET.ParseError as e:
            print(e)
        else:
            if self._validate_data(tree):
                root = tree.getroot()
                sq_type = root.find('./metadata/type').text
                if sq_type == 'dict':
                    seq = {i.attrib['key']: int(i.text) for i in root.findall(
                        './sequence/el'
                    )}
                else:
                    seq = [int(i.text) for i in root.findall(
                        './sequence/el'
                    )]

                return dict(
                    sequence=seq,
                    metadata=dict(
                        type=sq_type,
                        seq_type=root.find('./metadata/seq_type').text,
                        len=len(seq),
                        el_type='int',
                        date_created=root.find(
                            './metadata/date_created'
                        ).text,
                        date_modified=root.find(
                            './metadata/date_modified'
                        ).text,
                        author=root.find('./metadata/author').text,
                        min=int(root.find('./metadata/min').text),
                        max=int(root.find('./metadata/max').text)
                    )
                )


class JSONSerializer(Serializer):
    @staticmethod
    def _validate_data(data):
        if (
            data.get('sequence') and
            data.get('metadata') and
            data.get('metadata').get('type') and
            data.get('metadata').get('seq_type') and
            data.get('metadata').get('len') and
            data.get('metadata').get('el_type') and
            data.get('metadata').get('author') and
            'min' in data.get('metadata').keys() and
            data.get('metadata').get('max')
        ):
            return True
        return False

    @staticmethod
    def encode(sequence, s_type, seq_type, cr_time, author, min_el, max_el):
        return dict(
            sequence=sequence,
            metadata=dict(
                type=s_type,
                seq_type=seq_type,
                len=len(sequence),
                el_type='int',
                date_created=cr_time,
                date_modified=datetime.today().strftime(TIME_FORMAT),
                author=author,
                min=min_el,
                max=max_el
                )
            )

    def decode(self, path):
        try:
            json_data = json.load(path)
        except json.decoder.JSONDecodeError as e:
            print(e)
        else:
            if self._validate_data(json_data):
                return json_data


class BaseGenerator:
    __slots__ = ['max_length']

    def __init__(self, max_length=100):
        if isinstance(max_length, int) and max_length > 0:
            self.max_length = max_length
        else:
            raise InvalidTypeError(f'{self.__class__.__name__} can not process'
                                   f'  {type(max_length)}.')

    def __repr__(self):
        return f'{self.__class__.__name__}'

    def __check_seq_length(self, length):
        if length < self.max_length:
            return True
        else:
            raise InvalidSequenceLength('Items quantity should be less than '
                                        f'{self.max_length}.')

    def _custom_range(self, start, stop=None, step=1):
        if stop is None:
            stop = start
            start = 0
        elif not all(isinstance(i, int) for i in (start, stop, step)):
            raise InvalidTypeError('Only integer type values can be processed.')
        elif step < 0:
            raise InvalidValueError("Step should be greater than zero.")
        elif start > stop:
            raise InvalidValueError("Stop should be greater than start.")

        remainder = (stop - start) % step
        seq_length = (stop - start) // step
        length = seq_length if remainder == 0 else seq_length + 1

        if self.__check_seq_length(length):
            n = start
            while n < stop:
                yield int(n)
                n += step

    @staticmethod
    def __max_in_range(start, stop, step):
        if stop is None:
            stop = start
            start = 0
        elif not all(isinstance(i, int) for i in (start, stop, step)):
            raise InvalidTypeError('Only integer type values can be processed.')
        elif step < 0:
            raise InvalidValueError("Step should be greater than zero.")
        elif start > stop:
            raise InvalidValueError("Stop should be greater than start.")

        return (stop - 1) - ((stop - 1) - start) % step

    def __check_equal_sequences(self, data_type, data, min_el, max_el, step):
        if data is not None:
            meta = data['metadata']
            json_step = ((meta['max'] - meta['min']) //
                         (meta['len'] - 1)) if data_type == 'range' else 0

            type_check = self._sequence_type_check(meta['type'])
            seq_type_check = meta['seq_type'] == data_type
            el_check = (meta['max'] == max_el and
                        meta['min'] == min_el)
            equal_check = (type_check and
                           seq_type_check and
                           el_check and
                           step == json_step)

            if equal_check:
                return True
        return False

    @staticmethod
    def __get_serializer(data_format: str) -> Serializer:
        if data_format == 'xml':
            serializer = XMLSerializer()
        elif data_format == 'json':
            serializer = JSONSerializer()
        else:
            raise InvalidValueError('Only json and xml data formats are '
                                    'acceptable.')
        return serializer

    @staticmethod
    def __get_path(data_format: str) -> str:
        if data_format == 'xml':
            file_path = XML_PATH
        elif data_format == 'json':
            file_path = JSON_PATH
        else:
            raise InvalidValueError('Only json and xml data formats are '
                                    'acceptable.')
        return file_path

    @staticmethod
    def __remove_unsupported_file(data_format):
        if not isinstance(data_format, str):
            raise InvalidValueError('First argument should be data format.')
        if os.path.exists(JSON_PATH) and data_format == 'xml':
            os.remove(JSON_PATH)
        elif os.path.exists(XML_PATH) and data_format == 'json':
            os.remove(XML_PATH)

    def generate_sequence(self, data_format, start, stop=None, step=1):
        self.__remove_unsupported_file(data_format)
        serializer = self.__get_serializer(data_format)
        file_path = self.__get_path(data_format)

        max_element = self.__max_in_range(start, stop, step)
        if stop is None:
            stop = start
            start = 0
        sequence = None

        with open(file_path, 'a+') as file:
            creation_time = os.path.getctime(file_path)
            cr_time = datetime.fromtimestamp(creation_time)
            file.seek(0)
            if os.path.getsize(file_path) != 0:
                data = serializer.decode(file)
                if self.__check_equal_sequences('range',
                                                data,
                                                start,
                                                max_element,
                                                step):
                    sequence = data['sequence']
            if sequence is None:
                sequence = self._create_sequence(start, stop, step)

            args = (sequence, self._sequence_type(), 'range',
                    cr_time.strftime(TIME_FORMAT), repr(self), start,
                    max_element)

            data = serializer.encode(*args)
            file.truncate(0)
            file.write(data) if data_format == 'xml' else json.dump(
                data, file
            )

    @staticmethod
    def __fibonacci(first, second, n) -> int:
        for i in range(n - 1):
            first, second = second, first + second
        return first

    def generate_fibonacci(self, data_format, first, second, length):
        self.__remove_unsupported_file(data_format)
        self.__check_seq_length(length)
        serializer = self.__get_serializer(data_format)
        file_path = self.__get_path(data_format)

        with open(file_path, 'a+') as file:
            sequence = None
            creation_time = os.path.getctime(file_path)
            cr_time = datetime.fromtimestamp(creation_time)
            file.seek(0)
            if os.path.getsize(file_path) != 0:
                data = serializer.decode(file)
                if self.__check_equal_sequences('fibonacci',
                                                data,
                                                first,
                                                self.__fibonacci(first,
                                                                 second,
                                                                 length - 1),
                                                0):
                    sequence = data['sequence']
            if sequence is None:
                fib_sequence = [first, second]
                for i in range(3, length + 1):
                    fib_sequence.append(self.__fibonacci(first, second, i))
                sequence = self._generate_fibonacci(fib_sequence)

            args = (sequence, self._sequence_type(), 'fibonacci',
                    cr_time.strftime(TIME_FORMAT), repr(self), first,
                    int(max(sequence)))

            data = serializer.encode(*args)
            file.truncate(0)
            file.write(data) if data_format == 'xml' else json.dump(
                data, file
            )

    def get_sequence(self):
        if os.path.exists(XML_PATH) and os.path.getsize(XML_PATH) != 0:
            data_format = 'xml'
        elif os.path.exists(JSON_PATH) and os.path.getsize(JSON_PATH) != 0:
            data_format = 'json'
        else:
            return []

        path = self.__get_path(data_format)
        coder = self.__get_serializer(data_format)

        with open(path, 'r') as file:
            data = coder.decode(file)
            if not data:
                raise InvalidValueError(f'Invalid decoded data structure.')
            elif not self._sequence_type_check(data['metadata']['type']):
                raise InvalidTypeError('File contains invalid sequence type.')
            elif data['metadata']['len'] > self.max_length:
                raise InvalidSequenceLength('Items quantity should be less'
                                            f' than {self.max_length}.')

            return data['sequence']

    @staticmethod
    def _create_sequence(start, stop, step):
        raise NotImplementedError

    @staticmethod
    def _generate_fibonacci(sequence):
        raise NotImplementedError

    @staticmethod
    def _sequence_type():
        raise NotImplementedError

    @staticmethod
    def _sequence_type_check(type_str):
        raise NotImplementedError


class ListGenerator(BaseGenerator):
    __slots__ = ['max_length']

    def _create_sequence(self, start, stop, step):
        return [_ for _ in self._custom_range(start, stop, step)]

    def _generate_fibonacci(self, sequence):
        return [_ for _ in sequence]

    @staticmethod
    def _sequence_type():
        return type([]).__name__

    @staticmethod
    def _sequence_type_check(type_str):
        return any(i == type_str for i in (type([]).__name__,
                                           type(()).__name__,
                                           type(set()).__name__))


class TupleGenerator(ListGenerator):
    __slots__ = ['max_length']

    @staticmethod
    def _sequence_type():
        return type(()).__name__

    def get_sequence(self):
        return tuple(super(TupleGenerator, self).get_sequence())


class SetGenerator(ListGenerator):
    __slots__ = ['max_length']

    @staticmethod
    def _sequence_type():
        return type(set()).__name__

    @staticmethod
    def _generate_fibonacci(sequence):
        raise FibonacciError

    def _sequence_type_check(self, type_str):
        return type_str == self._sequence_type()

    def get_sequence(self):
        return set(super(SetGenerator, self).get_sequence())


class DictGenerator(BaseGenerator):
    __slots__ = ['max_length']

    def _create_sequence(self, start, stop, step):
        return {f'{i}': i for i in self._custom_range(start, stop, step)}

    @staticmethod
    def _generate_fibonacci(sequence):
        raise FibonacciError

    @staticmethod
    def _sequence_type():
        return type({}).__name__

    def _sequence_type_check(self, type_str):
        return type_str == self._sequence_type()


RANDOM_DATETIME = datetime(
    randint(1970, 3000),
    randint(1, 12),
    randint(1, 29),
    randint(0, 23),
    randint(0, 59)
)
LETTERS_DIGITS = ''.join([ascii_letters, digits])


def test_correct_sequence_get_generation():
    incorrect_test_values = [randint(50, 120) for _ in range(20)]
    try:
        for i in incorrect_test_values:
            list_gen = ListGenerator(i)
            tuple_gen = TupleGenerator(i)
            set_gen = SetGenerator(i)
            dict_gen = DictGenerator(i)

            open(JSON_PATH, 'w').close()
            open(XML_PATH, 'w').close()
            assert list_gen.get_sequence() == []

            list_gen.generate_sequence('xml', randint(121, 250))
            tuple_gen.generate_sequence('xml', randint(121, 250))
            set_gen.generate_sequence('json', randint(121, 250))
            dict_gen.generate_sequence('json', randint(121, 250))

    except BaseException as e:
        if not isinstance(e, InvalidSequenceLength):
            print(e)

    correct_test_values = [randint(121, 250) for _ in range(20)]
    for i in correct_test_values:
        list_gen = ListGenerator(i)
        tuple_gen = TupleGenerator(i)
        set_gen = SetGenerator(i)
        dict_gen = DictGenerator(i)
        list_gen.generate_sequence('xml', 68, 121, 3)
        with open(XML_PATH, 'r') as seq_file:
            xml_data = XMLSerializer().decode(seq_file)
            generated_list = list(xml_data['sequence'])
            expected_list = [k for k in range(68, 121, 3)]
            assert generated_list == expected_list
            assert expected_list == list_gen.get_sequence()
        tuple_rand_value = randint(50, 120)
        tuple_gen.generate_sequence('json', tuple_rand_value)
        with open(JSON_PATH, 'r') as seq_file:
            json_data = JSONSerializer().decode(seq_file)
            generated_tuple = tuple(json_data['sequence'])
            expected_tuple = tuple(k for k in range(tuple_rand_value))
            assert generated_tuple == expected_tuple
            assert expected_tuple == tuple_gen.get_sequence()
        set_rand_value = randint(50, 120)
        set_gen.generate_sequence('json', set_rand_value)
        with open(JSON_PATH, 'r') as seq_file:
            json_data = JSONSerializer().decode(seq_file)
            generated_set = set(json_data['sequence'])
            expected_set = set(k for k in range(set_rand_value))
            assert generated_set == expected_set
            assert expected_set == set_gen.get_sequence()
        dict_rand_value = randint(50, 120)
        dict_gen.generate_sequence('xml', dict_rand_value)
        with open(XML_PATH, 'r') as seq_file:
            xml_data = XMLSerializer().decode(seq_file)
            generated_dict = xml_data['sequence']
            expected_dict = {f'{k}': k for k in range(dict_rand_value)}
            assert generated_dict == expected_dict
            assert expected_dict == dict_gen.get_sequence()

    print('Reading from file and getting sequences tests finished.')


def test_types_compatibility():
    correct_test_values = [randint(121, 250) for _ in range(20)]
    for i in correct_test_values:
        list_gen = ListGenerator(i)
        tuple_gen = TupleGenerator(i)
        set_gen = SetGenerator(i)
        dict_gen = DictGenerator(i)
        list_rand_value = randint(50, 120)
        list_gen.generate_sequence('json', list_rand_value)
        assert tuple_gen.get_sequence() == tuple(list_gen.get_sequence())
        assert list_gen.get_sequence() == list(tuple_gen.get_sequence())
        list_gen.generate_fibonacci('xml', 2, 3, 5)
        assert tuple_gen.get_sequence() == tuple(list_gen.get_sequence())
        assert list_gen.get_sequence() == list(tuple_gen.get_sequence())

        try:
            dict_gen.get_sequence()
        except BaseException as e:
            if not isinstance(e, InvalidTypeError):
                print(e)

        try:
            set_gen.get_sequence()
        except BaseException as e:
            if not isinstance(e, InvalidTypeError):
                print(e)

        dict_rand_value = randint(50, 120)
        dict_gen.generate_sequence('json', dict_rand_value)

        try:
            list_gen.get_sequence()
        except BaseException as e:
            if not isinstance(e, InvalidTypeError):
                print(e)

        try:
            tuple_gen.get_sequence()
        except BaseException as e:
            if not isinstance(e, InvalidTypeError):
                print(e)

        try:
            set_gen.get_sequence()
        except BaseException as e:
            if not isinstance(e, InvalidTypeError):
                print(e)

        try:
            dict_gen.generate_fibonacci('xml', 2, 5, 7)
        except BaseException as e:
            if not isinstance(e, FibonacciError):
                print(e)

        try:
            set_gen.generate_fibonacci('xml', 2, 5, 7)
        except BaseException as e:
            if not isinstance(e, FibonacciError):
                print(e)

    print('Compatibility tests finished.')


def test_non_acceptable_arguments():
    for z in range(100):
        test_value = choice([
            randint(-10000000000000000, -1),
            ''.join(choice(LETTERS_DIGITS) for _ in range(1, 5999)),
            False,
            0,
            RANDOM_DATETIME,
            lambda x: x + 1])
        try:
            ListGenerator(test_value)
            TupleGenerator(test_value)
            SetGenerator(test_value)
            DictGenerator(test_value)
        except Exception as e:
            if not isinstance(e, InvalidTypeError):
                print(e)
    print('Non acceptable arguments tests finished.')


def test_list_set_tuple_dict_generator():
    test_correct_sequence_get_generation()
    test_types_compatibility()
    test_non_acceptable_arguments()
