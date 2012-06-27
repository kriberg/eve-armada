from django.db import models
from eve.ccpmodels import *

class EveCentralOrderManager(models.Manager):
    def get_buy_orders(self):
        return self.filter(bid=0)
    def get_sell_orders(self):
        return self.filter(bid=1)

class EveCentralOrder(models.Model):
    id = models.AutoField(primary_key=True)
    orderid = models.IntegerField()
    region = models.ForeignKey(MapRegion)
    system = models.ForeignKey(MapSolarsystem)
    station = models.ForeignKey(MapDenormalize)
    item = models.ForeignKey(InvType)
    bid = models.BooleanField()
    price = models.DecimalField(max_digits=20, decimal_places=2)
    minvolume = models.IntegerField()
    volremain = models.IntegerField()
    volenter = models.IntegerField()
    issued = models.DateTimeField()
    duration = models.IntegerField()
    order_range = models.IntegerField()
    reported_time = models.DateTimeField()

class ItemRegionFloatingPrice(models.Model):
    id = models.AutoField(primary_key=True)
    item = models.ForeignKey(InvType)
    region = models.ForeignKey(MapRegion)
    buy_volume = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    buy_average = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    buy_maximum = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    buy_minimum = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    buy_stddev = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    buy_median = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    buy_percentile = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    sell_volume = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    sell_average = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    sell_maximum = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    sell_minimum = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    sell_stddev = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    sell_median = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    sell_percentile = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    timestamp = models.DateTimeField(auto_now=True)
    def __unicode__(self):
        return '%s @ %s' % (self.item, self.region)
    def to_dict(self):
        return {'item': self.item.typename,
                'region': self.region.regionname,
                'buy_volume': self.buy_volume,
                'buy_average': self.buy_average,
                'buy_maximum': self.buy_maximum,
                'buy_minimum': self.buy_minimum,
                'buy_stddev': self.buy_stddev,
                'buy_median': self.buy_median,
                'buy_percentile': self.buy_percentile,
                'sell_volume': self.sell_volume,
                'sell_average': self.sell_average,
                'sell_maximum': self.sell_maximum,
                'sell_minimum': self.sell_minimum,
                'sell_stddev': self.sell_stddev,
                'sell_median': self.sell_median,
                'sell_percentile': self.sell_percentile,
                'timestamp': self.timestamp}

class ItemSystemFloatingPrice(models.Model):
    id = models.AutoField(primary_key=True)
    item = models.ForeignKey(InvType)
    system = models.ForeignKey(MapSolarsystem)
    buy_volume = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    buy_average = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    buy_maximum = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    buy_minimum = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    buy_stddev = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    buy_median = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    buy_percentile = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    sell_volume = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    sell_average = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    sell_maximum = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    sell_minimum = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    sell_stddev = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    sell_median = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    sell_percentile = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    timestamp = models.DateTimeField(auto_now=True)
    def __unicode__(self):
        return '%s @ %s' % (self.item, self.system)
    def to_dict(self):
        return {'item': self.item.typename,
                'system': self.system.solarsystemname,
                'buy_volume': self.buy_volume,
                'buy_average': self.buy_average,
                'buy_maximum': self.buy_maximum,
                'buy_minimum': self.buy_minimum,
                'buy_stddev': self.buy_stddev,
                'buy_median': self.buy_median,
                'buy_percentile': self.buy_percentile,
                'sell_volume': self.sell_volume,
                'sell_average': self.sell_average,
                'sell_maximum': self.sell_maximum,
                'sell_minimum': self.sell_minimum,
                'sell_stddev': self.sell_stddev,
                'sell_median': self.sell_median,
                'sell_percentile': self.sell_percentile,
                'timestamp': self.timestamp}
