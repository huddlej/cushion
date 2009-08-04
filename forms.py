from django import forms


class DocumentForm(forms.Form):
    title = forms.CharField()
    content = forms.CharField(widget=forms.Textarea(attrs={"cols": 80,
                                                           "rows": 20}))
