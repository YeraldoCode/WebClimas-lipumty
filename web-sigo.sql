CREATE DATABASE lipumty_climas;
USE lipumty_climas;

CREATE TABLE Servicios (
	ID INT PRIMARY KEY,
    Marca_AC VARCHAR(50),
    Cliente VARCHAR(100)
    );

-- Consultar tabla completa de Servicios
SELECT*FROM Vehiculos;

CREATE TABLE Vehiculos ( 
	IdVehiculo INT PRIMARY KEY,
    Unidad_negocio VARCHAR(100),
    Serial VARCHAR(50),
    Marca VARCHAR(50),
    Modelo VARCHAR(50),
    Asientos INT,
    Tipo_vehiculo VARCHAR(50),
    Gpo_estatus VARCHAR(50),
    Uso VARCHAR(50),
    Estatus VARCHAR(50),
    Descripcion VARCHAR(255),
    Aire VARCHAR(10),
    Jala VARCHAR(10),
    Mochila VARCHAR(10),
    Conversion_Reparacion VARCHAR(50),
    Reinsidente VARCHAR(10)
    );
    
SELECT 
    V.*, S.Marca_AC, S.Cliente
FROM 
    Vehiculos V
JOIN 
    Servicios S ON V.IdVehiculo = S.ID;

