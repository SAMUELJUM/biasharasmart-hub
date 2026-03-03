from django.contrib import admin
from .models import Business, Customer, Supplier

admin.site.register(Business)
admin.site.register(Customer)
admin.site.register(Supplier)