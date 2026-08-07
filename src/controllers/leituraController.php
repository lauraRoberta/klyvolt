<?php

namespace GestaoEnergia\Controllers;

use GestaoEnergia\Models\Leitura;
use GestaoEnergia\Models\Consumo;
use GestaoEnergia\Models\Custo;

class LeituraController
{
    private Leitura $leitura;
    private Consumo $consumo;
    private Custo $custo;

    public function __construct()
    {
        $this->leitura = new Leitura();
        $this->consumo = new Consumo();
        $this->custo = new Custo();
    }

    public function registrar(array $dados): array
    {
        try {
            if (empty($dados['id_maquina']) || empty($dados['valor_kwh'])) {
                return ['success' => false, 'message' => 'Dados incompletos'];
            }

            $ultima = $this->leitura->findLastByMaquina($dados['id_maquina']);
            if ($ultima && $dados['valor_kwh'] < $ultima['valor_medido_kwh']) {
                return [
                    'success' => false,
                    'message' => 'Valor não pode ser menor que a última leitura: ' . $ultima['valor_medido_kwh'] . ' kWh'
                ];
            }

            $idLeitura = $this->leitura->registrar(
                $dados['id_maquina'],
                $dados['id_usuario'] ?? 1,
                $dados['valor_kwh'],
                $dados['observacao'] ?? null
            );

            if ($ultima) {
                $consumoKwh = $dados['valor_kwh'] - $ultima['valor_medido_kwh'];
                
                $idConsumo = $this->consumo->criarConsumo(
                    $ultima['data_leitura'],
                    date('Y-m-d H:i:s'),
                    $consumoKwh,
                    $dados['id_maquina'],
                    $ultima['id_leitura'],
                    $idLeitura
                );

                // Buscar tarifa (ajustado para PostgreSQL)
                $stmt = $this->custo->db->prepare("
                    SELECT t.id_tarifa, t.valor_tarifa
                    FROM TARIFA t
                    JOIN LOCALIZACAO l ON t.id_localizacao = l.id_localizacao
                    JOIN SETOR s ON l.id_localizacao = s.id_localizacao
                    JOIN MAQUINA m ON s.id_setor = m.id_setor
                    WHERE m.id_maquina = ? 
                    AND t.data_inicio_vigencia <= NOW() 
                    AND t.data_fim_vigencia >= NOW()
                    LIMIT 1
                ");
                $stmt->execute([$dados['id_maquina']]);
                $tarifa = $stmt->fetch();

                if ($tarifa) {
                    $valorTotal = $consumoKwh * $tarifa['valor_tarifa'];
                    $this->custo->calcularCusto($idConsumo, $tarifa['id_tarifa'], $valorTotal);
                }
            }

            return ['success' => true, 'message' => 'Leitura registrada com sucesso!', 'id' => $idLeitura];
        } catch (\Exception $e) {
            return ['success' => false, 'message' => 'Erro: ' . $e->getMessage()];
        }
    }

    public function listarPorMaquina(int $idMaquina): array
    {
        return $this->leitura->findByMaquina($idMaquina);
    }
}