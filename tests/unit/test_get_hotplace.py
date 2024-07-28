import unittest
from placeholder_hotplace import get_hotplace

class TestGetHotplace(unittest.TestCase):
    def test_handler(self):
        event = {
            'pathParameters': {
                'id': '강남구'
            }
        }
        context = {}
        response = get_hotplace.handler(event, context)
        self.assertEqual(response['statusCode'], 200)

if __name__ == '__main__':
    unittest.main()