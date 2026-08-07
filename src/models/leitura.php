<?php

namespace GestaoEnergia\Models;

class Leitura extends Model
{
    protected string $table = 'LEITURA';
    protected string $primaryKey = 'Id_leitura';

    public function findByMaquina(int $idMaquina): array
    {
        $stmt = $this->db->prepare("SELECT * FROM {$this->table} WHERE Id_maquina = ? ORDER BY data_leitura DESC");
        $stmt->execute([$idMaquina]);
        return $stmt->fetchAll();
    }

    public function findLastByMaquina(int $idMaquina): ?array
    {
        $stmt = $this->db->prepare("SELECT * FROM {$this->table} WHERE Id_maquina = ? ORDER BY Id_leitura DESC LIMIT 1");
        $stmt->execute([$idMaquina]);
        return $stmt->fetch() ?: null;
    }

    public function registrar(int $idMaquina, int $idUsuario, float $valor, ?string $obs = null): int
    {
        return $this->create([
            'data_leitura' => date('Y-m-d H:i:s'),
            'valor_medido_kwh' => $valor,
            'observacao_leitura' => $obs,
            'Id_maquina' => $idMaquina,
            'Id_usuario' => $idUsuario
        ]);
    }
}