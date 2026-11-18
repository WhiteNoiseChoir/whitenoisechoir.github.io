import unittest
from scripts.ingest_private_pixabay_music import validate_page, validate_download_url


class PrivateMusicIngestTests(unittest.TestCase):
    def test_source_page(self):
        self.assertEqual(validate_page("https://pixabay.com/music/modern-classical-relaxing-piano-music-248868/"),
                         "https://pixabay.com/music/modern-classical-relaxing-piano-music-248868/")
        for value in ("https://evil.example/music/x/", "http://pixabay.com/music/a-b/",
                      "https://pixabay.com.evil.example/music/x/",
                      "https://pixabay.com/music/"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_page(value)

    def test_download_host_restrictions(self):
        self.assertEqual(validate_download_url("https://cdn.pixabay.com/download/audio/2024/09/01/example.mp3"),
                         "https://cdn.pixabay.com/download/audio/2024/09/01/example.mp3")
        for value in ("http://cdn.pixabay.com/download/audio/test.mp3",
                      "https://cdn.pixabay.com.evil.example/download/audio/test.mp3",
                      "https://127.0.0.1/test.mp3",
                      "https://cdn.pixabay.com/download/image.jpg",
                      "https://user:pass@cdn.pixabay.com/download/audio/ok.mp3"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_download_url(value)


if __name__ == "__main__":
    unittest.main()
