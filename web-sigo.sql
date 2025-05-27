create table servicios (
    id int primary key,
    marca_ac varchar(50)
);

create table vehiculos (
    idvehiculo int primary key,
    serial varchar(50),
    marca varchar(50),
    modelo varchar(50),
    asientos int,
    motor varchar(50),
    anio int,
    tipo_vehiculo varchar(50),
    gpo_estatus varchar(50),
    uso varchar(50),
    estatus varchar(50),
    combustible varchar(30),
    eco varchar(30),
    placas varchar(30),
    placas_federales varchar(30),
    descripcion varchar(255),
    aire varchar(10),
    jala varchar(10),
    mochila varchar(10),
    conversion_reparacion varchar(50),
    reinsidente varchar(10)
);

select 
    v.*, s.marca_ac
from 
    vehiculos v
join 
    servicios s on v.idvehiculo = s.id;

