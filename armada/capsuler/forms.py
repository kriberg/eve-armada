from django.forms.models import BaseModelFormSet, ModelForm
from django.forms import ValidationError
from django.forms.forms import NON_FIELD_ERRORS
from django import forms
from armada.lib.api import private
from traceback import format_exc

from armada.capsuler.models import UserAPIKey

class UserAPIKeyForm(ModelForm):
    keytype = forms.CharField(required=False, widget=forms.HiddenInput())
    accessmask = forms.CharField(required=False, widget=forms.HiddenInput())
    expires = forms.CharField(required=False, widget=forms.HiddenInput(), initial='2100-12-31 23:59')
    def __init__(self, *args, **kwargs):
        super(UserAPIKeyForm, self).__init__(*args, **kwargs)
        if self.instance:
            self.keytype = forms.CharField(required=False)
            self.accessmask = forms.CharField(required=False)
            self.expires = forms.CharField(required=False)
    class Meta:
        model = UserAPIKey
        exclude = ('user', )

class UserAPIKeyFormSet(BaseModelFormSet):
    keydata = {}
    def clean(self):
        super(UserAPIKeyFormSet, self).clean()
        for form in self.forms:
            if 'DELETE' in form.cleaned_data:
                if form.cleaned_data['DELETE']:
                    continue
            keyid = form.cleaned_data['keyid']
            vcode = form.cleaned_data['verification_code']
            if not keyid.isdigit():
                form.errors['keyid'] = ('Invalid keyID',)
            if not vcode.isalnum():
                form.errors['verification_code'] = ('Invalid vCode',)
            if len(form.errors.keys()) > 0:
                raise ValidationError('Invalid API key')
            try:
                kinfo = private.get_apikey_info(keyid, vcode)
                self.keydata[keyid] = {}
                self.keydata[keyid]['keytype'] = kinfo.key.type
                self.keydata[keyid]['accessmask'] = kinfo.key.accessMask
                self.keydata[keyid]['expires'] = kinfo.key.expires
            except Exception, ex:
                form._errors[NON_FIELD_ERRORS] = form.error_class(['Invalid API key',])
                print format_exc(ex)
                raise ValidationError('Invalid API key')

