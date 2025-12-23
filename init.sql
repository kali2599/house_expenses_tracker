-- Create registro_spese table
CREATE TABLE registro_spese (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT DEFAULT (DATE(CURRENT_TIMESTAMP)),
    categoria TEXT,
    nota TEXT,
    importo REAL
);

-- Example trigger to ensure 'data' is stored in 'YYYY-MM-DD' format (if needed)
-- This is redundant with DEFAULT (DATE(CURRENT_TIMESTAMP)) but included for clarity
CREATE TRIGGER IF NOT EXISTS set_data_date
AFTER INSERT ON registro_spese
FOR EACH ROW
BEGIN
    UPDATE registro_spese
    SET data = DATE(CURRENT_TIMESTAMP)
    WHERE id = NEW.id;
END;



-- Create  spese_mensili table
CREATE TABLE spese_mensili (
    mese TEXT PRIMARY KEY,
    entrate REAL,
    spesa REAL,
    pasti_fuori REAL,
    svago REAL,
    shopping REAL,
    inaspettate REAL,
    varie REAL,
    salute REAL,
    vacanze REAL,
    uscite_variabili REAL,
    cometa REAL,
    assicurazioni REAL,
    condominio REAL,
    luce REAL,
    gas REAL,
    mutuo REAL,
    lenti REAL,
    telefonia REAL,
    parrucchiere REAL,
    palestra REAL,
    uscite_fisse REAL,
    uscite_totali REAL,
    delta REAL
);

-- Insert initial data into the spese_mensili table
INSERT INTO spese_mensili(mese, entrate, spesa, pasti_fuori, svago, shopping, inaspettate, varie, salute, vacanze, uscite_variabili, cometa, assicurazioni, condominio, luce, gas, mutuo,
lenti, telefonia, parrucchiere, palestra, uscite_fisse, uscite_totali, delta)
VALUES("GIUGNO", 4576, 311, 52.7, 167.6, 102, 56, 75, 0, 0, 764.3, 27, 0, 54.5, 0, 0, 0, 26, 10, 19, 103.3, 239.8, 1004.1, 3571.9);

-- Create trigger to update uscite_variabili
CREATE TRIGGER update_uscite_variabili AFTER UPDATE OF spesa, pasti_fuori, svago, shopping, inaspettate, varie, salute, vacanze 
ON spese_mensili 
FOR EACH ROW 
BEGIN
UPDATE spese_mensili
SET uscite_variabili = ROUND(
    uscite_variabili + 
    (new.spesa - old.spesa) +
    (new.pasti_fuori - old.pasti_fuori) +
    (new.svago - old.svago) +
    (new.shopping - old.shopping) +
    (new.inaspettate - old.inaspettate) +
    (new.varie - old.varie) +
    (new.salute - old.salute) +
    (new.vacanze - old.vacanze),
    1
)
WHERE mese = old.mese;
END;

-- Create trigger to update uscite_fisse
CREATE TRIGGER update_uscite_fisse AFTER UPDATE OF cometa, assicurazioni, condominio, luce, gas, mutuo, lenti, telefonia, parrucchiere, palestra
ON spese_mensili
FOR EACH ROW 
BEGIN
UPDATE spese_mensili
SET uscite_fisse = ROUND(
    uscite_fisse + 
    (new.cometa - old.cometa) +
    (new.assicurazioni - old.assicurazioni) +
    (new.condominio - old.condominio) +
    (new.luce - old.luce) +
    (new.gas - old.gas) +
    (new.mutuo - old.mutuo) +
    (new.lenti - old.lenti) +
    (new.telefonia - old.telefonia) +
    (new.parrucchiere - old.parrucchiere) +
    (new.palestra - old.palestra),
    1
)
WHERE mese = old.mese;
END;    

-- Create trigger to update uscite_totali
CREATE TRIGGER update_uscite_totali AFTER UPDATE OF uscite_variabili, uscite_fisse
ON spese_mensili
FOR EACH ROW 
BEGIN
UPDATE spese_mensili
set uscite_totali = ROUND(
    uscite_totali + 
    (new.uscite_variabili - old.uscite_variabili) +
    (new.uscite_fisse - old.uscite_fisse),
    1)
WHERE mese = old.mese;
END;    

-- Create trigger to update delta
CREATE TRIGGER update_delta AFTER UPDATE OF uscite_totali, entrate
ON spese_mensili
FOR EACH ROW 
BEGIN
UPDATE spese_mensili
SET delta = ROUND(entrate - uscite_totali, 1)
WHERE mese = old.mese; 
END;