from django import forms


class CreatePaste(forms.Form):
    code = forms.CharField(
        max_length=16384,
        widget=forms.Textarea(attrs={
            'class': 'form-control container w-75 bg-light text-dark',
            'style': 'resize: none',
            'placeholder': 'Code...'
        }),
        label=''
    )


class DeletePaste(forms.Form):
    key = forms.CharField(
        max_length=16,
        widget=forms.TextInput(attrs={
            'class': 'form-control container w-50 bg-light text-dark',
            'placeholder': 'Type the key in the URL...'
        }),
        label=''
    )
