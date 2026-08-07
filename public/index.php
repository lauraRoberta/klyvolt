<?php

spl_autoload_register(function ($class) {
    $prefix = 'GestaoEnergia\\';
    $base_dir = __DIR__ . '/../src/';
    $relative_class = substr($class, strlen($prefix));
    $file = $base_dir . str_replace('\\', '/', $relative_class) . '.php';
    if (file_exists($file)) require $file;
});

use GestaoEnergia\Controllers\LeituraController;

try {
    // CONEXÃO POSTGRESQL
    $pdo = new PDO('pgsql:host=localhost;port=5432;dbname=gestao_energetica', 'postgres', '');
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    echo "✅ Conectado ao PostgreSQL com sucesso!<br><br>";
} catch (PDOException $e) {
    die("❌ Erro ao conectar: " . $e->getMessage());
}

// ============================================================
// LISTAR EMPRESAS
// ============================================================
echo "<h2>🏢 Empresas</h2>";
$stmt = $pdo->query("SELECT * FROM EMPRESA");
$empresas = $stmt->fetchAll();

if (count($empresas) > 0) {
    echo "<table border='1' cellpadding='5'>";
    echo "<tr><th>ID</th><th>Nome</th><th>Email</th></tr>";
    foreach ($empresas as $e) {
        // POSTGRESQL USA LETRAS MINÚSCULAS NOS CAMPOS!
        echo "<tr><td>{$e['id_empresa']}</td><td>{$e['nome_empresa']}</td><td>{$e['email_empresa']}</td></tr>";
    }
    echo "</table>";
} else {
    echo "Nenhuma empresa cadastrada.<br>";
}

// ============================================================
// LISTAR MÁQUINAS
// ============================================================
echo "<h2>⚙️ Máquinas</h2>";
$stmt = $pdo->query("SELECT * FROM MAQUINA");
$maquinas = $stmt->fetchAll();

if (count($maquinas) > 0) {
    echo "<table border='1' cellpadding='5'>";
    echo "<tr><th>ID</th><th>Nome</th><th>Descrição</th></tr>";
    foreach ($maquinas as $m) {
        echo "<tr><td>{$m['id_maquina']}</td><td>{$m['nome_maquina']}</td><td>{$m['descricao_maquina']}</td></tr>";
    }
    echo "</table>";
} else {
    echo "Nenhuma máquina cadastrada.<br>";
}

// ============================================================
// FORMULÁRIO PARA REGISTRAR LEITURA
// ============================================================
echo "<h2>📊 Nova Leitura</h2>";
echo "<form method='POST'>";
echo "Máquina: <select name='id_maquina'>";
$stmt = $pdo->query("SELECT id_maquina, nome_maquina FROM MAQUINA");
foreach ($stmt->fetchAll() as $m) {
    echo "<option value='{$m['id_maquina']}'>{$m['nome_maquina']}</option>";
}
echo "</select><br>";
echo "Valor (kWh): <input type='number' step='0.01' name='valor_kwh' required><br>";
echo "Observação: <input type='text' name='observacao'><br>";
echo "<button type='submit' name='registrar'>Registrar</button>";
echo "</form>";

// ============================================================
// PROCESSAR FORMULÁRIO
// ============================================================
if (isset($_POST['registrar'])) {
    $controller = new LeituraController();
    $resultado = $controller->registrar([
        'id_maquina' => $_POST['id_maquina'],
        'valor_kwh' => $_POST['valor_kwh'],
        'observacao' => $_POST['observacao'] ?? null,
        'id_usuario' => 1
    ]);
    
    echo "<h3 style='color:" . ($resultado['success'] ? 'green' : 'red') . "'>" . $resultado['message'] . "</h3>";
}

// ============================================================
// LISTAR ÚLTIMAS LEITURAS
// ============================================================
echo "<h2>📋 Últimas Leituras</h2>";
$stmt = $pdo->query("
    SELECT l.*, m.nome_maquina 
    FROM LEITURA l 
    JOIN MAQUINA m ON l.id_maquina = m.id_maquina 
    ORDER BY l.data_leitura DESC 
    LIMIT 10
");
$leituras = $stmt->fetchAll();

if (count($leituras) > 0) {
    echo "<table border='1' cellpadding='5'>";
    echo "<tr><th>Data</th><th>Valor (kWh)</th><th>Máquina</th></tr>";
    foreach ($leituras as $l) {
        echo "<tr><td>{$l['data_leitura']}</td><td>{$l['valor_medido_kwh']}</td><td>{$l['nome_maquina']}</td></tr>";
    }
    echo "</table>";
} else {
    echo "Nenhuma leitura registrada.<br>";
}