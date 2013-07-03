create view eve_invtypes_view as select i.typeid,
g.groupname,
i.typename,
i.description,
c.racename,
m.marketgroupname
from invtypes i, invgroups g, invmarketgroups m, chrraces c
where i.published=1 and
g.groupid=i.groupid and
m.marketgroupid=i.marketgroupid;
