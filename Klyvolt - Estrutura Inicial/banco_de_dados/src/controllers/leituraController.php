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
            // Validar
            if (empty($dados['id_maquina']) || empty($dados['valor_kwh'])) {
                return ['success' => false, 'message' => 'Dados incompletos'];
            }

            // Verificar última leitura
            $ultima = $this->leitura->findLastByMaquina($dados['id_maquina']);
            if ($ultima && $dados['valor_kwh'] < $ultima['valor_medido_kwh']) {
                return [
                    'success' => false,
                    'message' => 'Valor não pode ser menor que a última leitura: ' . $ultima['valor_medido_kwh'] . ' kWh'
                ];
            }

            // Registrar leitura
            $idLeitura = $this->leitura->registrar(
                $dados['id_maquina'],
                $dados['id_usuario'] ?? 1,
                $dados['valor_kwh'],
                $dados['observacao'] ?? null
            );

            // Se existia leitura anterior, calcular consumo
            if ($ultima) {
                $consumoKwh = $dados['valor_kwh'] - $ultima['valor_medido_kwh'];
                
                $idConsumo = $this->consumo->criarConsumo(
                    $ultima['data_leitura'],
                    date('Y-m-d H:i:s'),
                    $consumoKwh,
                    $dados['id_maquina'],
                    $ultima['Id_leitura'],
                    $idLeitura
                );

                // Buscar tarifa e calcular custo
                $stmt = $this->custo->db->prepare("
                    SELECT t.Id_tarifa, t.valor_tarifa
                    FROM TARIFA t
                    JOIN LOCALIZACAO l ON t.Id_localizacao = l.Id_localizacao
                    JOIN SETOR s ON l.Id_localizacao = s.Id_localizacao
                    JOIN MAQUINA m ON s.Id_setor = m.Id_setor
                    WHERE m.Id_maquina = ? 
                    AND t.data_inicio_vigencia <= NOW() 
                    AND t.data_fim_vigencia >= NOW()
                    LIMIT 1
                ");
                $stmt->execute([$dados['id_maquina']]);
                $tarifa = $stmt->fetch();

                if ($tarifa) {
                    $valorTotal = $consumoKwh * $tarifa['valor_tarifa'];
                    $this->custo->calcularCusto($idConsumo, $tarifa['Id_tarifa'], $valorTotal);
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