from django.dispatch import Signal

pre_init = Signal(providing_args=["data", "files", "initial", "prefix", "label_suffix", "empty_permitted"])
post_init = Signal(providing_args=["instance"])

pre_clean = Signal(providing_args=["data"])
post_clean = Signal(providing_args=["cleaned_data"])

pre_save = Signal(providing_args=["instance"])
post_save = Signal(providing_args=["instance"])
