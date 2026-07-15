from django.test.runner import DiscoverRunner


class CvTestRunner(DiscoverRunner):
    def build_suite(self, test_labels=None, **kwargs):
        if not test_labels:
            test_labels = ['cv']
        return super().build_suite(test_labels=test_labels, **kwargs)
