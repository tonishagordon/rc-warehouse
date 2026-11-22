-- One row per show in the warehouse.
select * from (
    values
        ('survivor',   'Survivor',      'CBS',               'survivoR R package (Daniel Oehm)', 'US seasons'),
        ('bigbrother', 'Big Brother',   'CBS',               'Wikipedia season pages',           'US seasons'),
        ('challenge',  'The Challenge', 'MTV / CBS / Paramount+', 'Wikipedia season pages',      'Main series + US spin-offs'),
        ('traitors',   'The Traitors',  'Peacock',           'Wikipedia season pages',           'US seasons')
) as t(show_name, show_title, network, data_source, scope)
