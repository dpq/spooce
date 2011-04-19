# echo "local infiniboard infiniboard md5" >> /etc/postgresql/8.4/main/pg_hba.conf
# invoke-rc.d postgresql restart
# su - postgres
$ createdb infiniboard
$ createuser -P infiniboard
$ createlang plpgsql infiniboard
$ psql -d infiniboard -f /usr/share/postgresql/8.4/contrib/postgis-1.5/postgis.sql
$ psql infiniboard
=# create table board(id serial primary key, uid integer);
=# create table "window"(id serial primary key, id_board integer, uid integer, meta varchar(256), args varchar(1024), hidden boolean, z int2);
=# select AddGeometryColumn('window', 'geom', -1, 'POLYGON', 2);
=# alter database infiniboard owner to infiniboard;
=# alter table board owner to infiniboard;
=# alter table "window" owner to infiniboard;
=# alter table geometry_columns owner to infiniboard;
=# alter table spatial_ref_sys owner to infiniboard;