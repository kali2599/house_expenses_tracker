-- Create registro_spese table
CREATE TABLE registro_spese (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT DEFAULT CURRENT_TIMESTAMP,
    categoria TEXT,
    nota TEXT,
    importo REAL
);


-- Create spese_mensili table
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
    investimenti REAL,
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
CREATE TRIGGER update_uscite_fisse AFTER UPDATE OF investimenti, assicurazioni, condominio, luce, gas, mutuo, lenti, telefonia, parrucchiere, palestra
ON spese_mensili
FOR EACH ROW 
BEGIN
UPDATE spese_mensili
SET uscite_fisse = ROUND(
    uscite_fisse + 
    (new.investimenti - old.investimenti) +
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


