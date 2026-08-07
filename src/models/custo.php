<?php

namespace GestaoEnergia\Models;

class Custo extends Model
{
    protected string $table = 'CUSTO';
    protected string $primaryKey = 'Id_custo';

    public function calcularCusto(int $idConsumo, int $idTarifa, float $valorTotal): int
    {
        return $this->create([
            'data_calculo' => date('Y-m-d H:i:s'),
            'valor_total' => $valorTotal,
            'Id_consumo' => $idConsumo,
            'Id_tarifa' => $idTarifa
        ]);
    }

    public function findByConsumo(int $idConsumo): ?array
    {
        $stmt = $this->db->prepare("SELECT * FROM {$this->table} WHERE Id_consumo = ?");
        $stmt->execute([$idConsumo]);
        return $stmt->fetch() ?: null;
    }
}