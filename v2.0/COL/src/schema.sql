drop table if exists vmTypes;
create table vmTypes (
		  tid integer primary key ,
		     cpu integer not null,
		        ram integer not null,
		           disk integer not null
		);

drop table if exists machines;
create table machines (
		  mid integer primary key autoincrement,
		     path text not null,
		        cpu integer not null,
		           ram integer not null,
			      disk integer not null,
		                 image_count integer not null,
		                    arch text not null
		);

drop table if exists images;
create table images (
		  iid integer primary key autoincrement,
		     path text not null
		);

drop table if exists clients;
create table clients (
                  cid integer primary key autoincrement,
                     vmid integer not null,
                        name text not null,
                         vtid integer not null,
                            mid integer not null,
			       count integer not null
                );  

drop table if exists volumes;
create table volumes (
                  volumeid integer primary key autoincrement,
		     status text not null,
                        name text not null,
                           vmid integer not null,
                              volsize integer not null,
			         volxml text not null
                );  
