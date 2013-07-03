import urllib2
from BeautifulSoup import BeautifulStoneSoup
from datetime import datetime, timedelta
from traceback import format_exc

from armada.core.models import *
from armada.eve.models import *

class EveCentral():
    endpoint='http://api.eve-central.com/api/marketstat'
    def _request(self, parameters):
        url = '%s?%s' % (self.endpoint, '&'.join(parameters))
        xml = urllib2.urlopen(url).read()
        soup = BeautifulStoneSoup(xml)
        return soup
    def get_items_region_price(self, items, region):
        fresh_pot = []
        for item in items:
            try:
                irfp = ItemRegionFloatingPrice.objects.get(item=item, region=region)
                if (datetime.now() - irfp.timestamp).total_seconds() > 3600:
                    fresh_pot.append(item)

            except ItemRegionFloatingPrice.DoesNotExist:
                fresh_pot.append(item)
        parameters = []
        if len(fresh_pot) > 0:
            for block in [fresh_pot[i:i+100] for i in range(0, len(fresh_pot)+1, 100)]:
                for item in block:
                    parameters.append('typeid=%d' % item.pk)
                parameters.append('regionlimit=%d' % region.pk)
                soup = self._request(parameters)
                for itemsoup in soup.findAll('type'):
                    bvol = itemsoup.find('buy').find('volume').renderContents()
                    bavg = itemsoup.find('buy').find('avg').renderContents()
                    bmax = itemsoup.find('buy').find('max').renderContents()
                    bmin = itemsoup.find('buy').find('min').renderContents()
                    bstddev = itemsoup.find('buy').find('stddev').renderContents()
                    bmedian = itemsoup.find('buy').find('median').renderContents()
                    bpercentile = itemsoup.find('buy').find('percentile').renderContents()
                    svol = itemsoup.find('sell').find('volume').renderContents()
                    savg = itemsoup.find('sell').find('avg').renderContents()
                    smax = itemsoup.find('sell').find('max').renderContents()
                    smin = itemsoup.find('sell').find('min').renderContents()
                    sstddev = itemsoup.find('sell').find('stddev').renderContents()
                    smedian = itemsoup.find('sell').find('median').renderContents()
                    spercentile = itemsoup.find('sell').find('percentile').renderContents()
                    item = InvType.objects.get(pk=itemsoup['id'])
                    try:
                        irfp = ItemRegionFloatingPrice.objects.get(item=item, region=region)
                    except ItemRegionFloatingPrice.DoesNotExist:
                        irfp = ItemRegionFloatingPrice(item = item, region=region)
                    irfp.buy_volume = bvol
                    irfp.buy_average = bavg
                    irfp.buy_maximum = bmax
                    irfp.buy_minimum = bmin
                    irfp.buy_stddev = bstddev
                    irfp.buy_median = bmedian
                    irfp.buy_percentile = bpercentile
                    irfp.sell_volume = svol
                    irfp.sell_average = savg
                    irfp.sell_maximum = smax
                    irfp.sell_minimum = smin
                    irfp.sell_stddev = sstddev
                    irfp.sell_median = smedian
                    irfp.sell_percentile = spercentile
                    irfp.timestamp = datetime.now()
                    irfp.save()
        return ItemRegionFloatingPrice.objects.filter(item__in=items, region=region)

    def get_items_system_price(self, items, system):
        fresh_pot = []
        fresh_pots = ItemSystemFloatingPrice.objects.filter(item__in=items,
                system=system,
                timestamp__gte=datetime.now()-timedelta(hours=1))
        new_pots = items.exclude(pk__in=[i.pk for i in fresh_pots])
        all_pots = [item for item in fresh_pots] + [item for item in new_pots]


        #print 'Fetching %d items for system %s' % (len(all_pots), system.solarsystemname)
        for block in [all_pots[i:i+64] for i in range(0, len(all_pots), 64)]:
            parameters = []
            for item in block:
                parameters.append('typeid=%d' % item.pk)
            parameters.append('usesystem=%d' % system.pk)
            try:
                soup = self._request(parameters)
            except Exception, ex:
                continue
            for itemsoup in soup.findAll('type'):
                bvol = itemsoup.find('buy').find('volume').renderContents()
                bavg = itemsoup.find('buy').find('avg').renderContents()
                bmax = itemsoup.find('buy').find('max').renderContents()
                bmin = itemsoup.find('buy').find('min').renderContents()
                bstddev = itemsoup.find('buy').find('stddev').renderContents()
                bmedian = itemsoup.find('buy').find('median').renderContents()
                bpercentile = itemsoup.find('buy').find('percentile').renderContents()
                svol = itemsoup.find('sell').find('volume').renderContents()
                savg = itemsoup.find('sell').find('avg').renderContents()
                smax = itemsoup.find('sell').find('max').renderContents()
                smin = itemsoup.find('sell').find('min').renderContents()
                sstddev = itemsoup.find('sell').find('stddev').renderContents()
                smedian = itemsoup.find('sell').find('median').renderContents()
                spercentile = itemsoup.find('sell').find('percentile').renderContents()
                item = InvType.objects.get(pk=itemsoup['id'])
                try:
                    isfp = ItemSystemFloatingPrice.objects.get(item=item, system=system)
                except ItemSystemFloatingPrice.DoesNotExist:
                    isfp = ItemSystemFloatingPrice(item = item, system=system)
                isfp.buy_volume = bvol
                isfp.buy_average = bavg
                isfp.buy_maximum = bmax
                isfp.buy_minimum = bmin
                isfp.buy_stddev = bstddev
                isfp.buy_median = bmedian
                isfp.buy_percentile = bpercentile
                isfp.sell_volume = svol
                isfp.sell_average = savg
                isfp.sell_maximum = smax
                isfp.sell_minimum = smin
                isfp.sell_stddev = sstddev
                isfp.sell_median = smedian
                isfp.sell_percentile = spercentile
                isfp.timestamp = datetime.now()
                isfp.save()
        return ItemSystemFloatingPrice.objects.filter(item__in=items, system=system)

    def get_systems_item_price(self, systems, item):
        for system in systems:
            self.get_items_system_price((item,), system)
        return ItemSystemFloatingPrice.objects.filter(item=item, system__in=systems)

    def get_regions_item_price(self, regions, item):
        for region in regions:
            self.get_items_region_price((item,), region)
        return ItemRegionFloatingPrice.objects.filter(item=item, region__in=regions)

    def get_system_matrix(self, items, systems):
        matrix = {}
        for system in systems:
            matrix[system] = self.get_items_system_price(items, system)
        return matrix
    def get_item_system_price(self, item, system):
        return self.get_items_system_price((item,), system)[0]
