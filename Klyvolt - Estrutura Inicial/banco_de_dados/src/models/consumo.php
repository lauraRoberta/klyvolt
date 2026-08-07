<?php

namespace GestaoEnergia\Models;

class Consumo extends Model
{
    protected string $table = 'CONSUMO';
    protected string $primaryKey = 'Id_consumo';

    public function criarConsumo(
        string $dataInicio,
        string $dataFim,
        float $consumoKwh,
        int $idMaquina,
        int $idLeituraInicial,
        int $idLeituraFinal
    ): int {
        return $this->create([
            'data_inicio' => $dataInicio,
            'data_fim' => $dataFim,
            'consumo_kwh' => $consumoKwh,
            'Id_maquina' => $idMaquina,
            'Id_leitura_inicial' => $idLeituraInicial,
            'Id_leitura_final' => $idLeituraFinal
        ]);
    }

    public function findByMaquina(int $idMaquina): array
    {
        $stmt = $this->db->prepare("SELECT * FROM {$this->table} WHERE Id_maquina = ? ORDER BY data_fim DESC");
        $stmt->execute([$idMaquina]);
        return $stmt->fetchAll();
    }
}