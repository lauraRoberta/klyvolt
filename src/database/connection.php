<?php

namespace GestaoEnergia\Database;

use PDO;
use PDOException;

class Connection
{
    private static ?Connection $instance = null;
    private PDO $pdo;

    private function __construct()
    {
        // CONFIGURAÇÃO PARA POSTGRESQL
        $host = 'localhost';
        $port = '5432';
        $dbname = 'gestao_energetica';
        $user = 'postgres';
        $password = ''; // Coloque sua senha aqui se tiver

        $dsn = "pgsql:host={$host};port={$port};dbname={$dbname}";

        try {
            $this->pdo = new PDO($dsn, $user, $password, [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            ]);
        } catch (PDOException $e) {
            die("Erro ao conectar ao PostgreSQL: " . $e->getMessage());
        }
    }

    public static function getInstance(): Connection
    {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    public function getPdo(): PDO
    {
        return $this->pdo;
    }
}