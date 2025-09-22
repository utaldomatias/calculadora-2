# Resumo de Custos AWS - Savings Plans

Aplicação Streamlit para processar arquivos CSV da Calculadora AWS e gerar resumos formatados de custos de reservas.

## Instalação

```bash
pip install -r requirements.txt
```

## Execução

```bash
streamlit run app.py
```

## Funcionalidades

- Upload de arquivos CSV da Calculadora AWS
- Processamento automático de recursos EC2, RDS e Lambda
- Cálculo de custos upfront e impostos (13,83%)
- Conversão para BRL com taxa de câmbio ajustável
- Geração de resumo formatado
- Download do resumo em formato texto

## Formato de Entrada

O CSV deve conter as colunas:
- Hierarquia de grupos
- Região
- Serviço
- Pagamento adiantado
- Mensal
- Resumo da configuração

## Exemplo de Uso

1. Faça upload do arquivo CSV exportado da Calculadora AWS
2. Ajuste a taxa de câmbio USD/BRL se necessário
3. Visualize o resumo gerado
4. Faça download do arquivo de resumo