import streamlit as st
import pandas as pd
import re
from typing import Dict, List, Tuple
from collections import defaultdict

def extract_instance_details(config_text: str, service: str) -> Dict:
    """Extrai detalhes das instâncias do texto de configuração"""
    details = {'quantidade': 1, 'tipo': 'N/A', 'specs': []}
    
    if "EC2" in service:
        # Extrair tipo de instância EC2
        instance_match = re.search(r'Instância do EC2 avançada \(([^)]+)\)|Advance EC2 instance \(([^)]+)\)', config_text)
        if instance_match:
            details['tipo'] = instance_match.group(1) or instance_match.group(2)
        
        # Extrair quantidade
        qty_match = re.search(r'Número de instâncias: (\d+)|Number of instances: (\d+)', config_text)
        if qty_match:
            details['quantidade'] = int(qty_match.group(1) or qty_match.group(2))
        
        # Extrair Pricing strategy
        pricing_match = re.search(r'Pricing strategy \(([^)]+)\)', config_text)
        pricing_strategy = pricing_match.group(1) if pricing_match else 'N/A'
        
        # Extrair Sistema operacional
        os_match = re.search(r'Sistema operacional \(([^)]+)\)|Operating system \(([^)]+)\)', config_text)
        os_system = (os_match.group(1) or os_match.group(2)) if os_match else 'N/A'
        
        details['specs'] = [pricing_strategy, os_system]
    
    elif "RDS" in service or "Aurora" in service:
        # Extrair tipo de instância RDS/Aurora
        instance_match = re.search(r'Tipo de instância \(([^)]+)\)|Instance type \(([^)]+)\)', config_text)
        if instance_match:
            details['tipo'] = instance_match.group(1) or instance_match.group(2)
        
        # Extrair número de nós
        nodes_match = re.search(r'Nós \((\d+)\)|Nodes \((\d+)\)', config_text)
        if nodes_match:
            details['quantidade'] = int(nodes_match.group(1) or nodes_match.group(2))
        
        # Extrair AZ
        az_config = 'Single AZ'
        if 'Multi' in config_text or 'multi' in config_text:
            az_config = 'Multi AZ'
        
        # Extrair opção de compra
        purchase_option = 'Reserved Instance'
        if 'OnDemand' in config_text:
            purchase_option = 'On Demand'
        elif 'No Upfront' in config_text:
            purchase_option = 'No Upfront'
        elif 'All Upfront' in config_text:
            purchase_option = 'All Upfront'
        
        # Extrair período
        period = '1 ano'
        if '3 year' in config_text.lower() or '3-year' in config_text.lower():
            period = '3 anos'
        
        # Engine type - usar o nome completo do serviço
        engine_type = service
        
        details['specs'] = [az_config, purchase_option, period, engine_type]
    
    elif "ElastiCache" in service:
        # Buscar por todos os tipos de instância (português e inglês)
        instance_types = re.findall(r'Tipo de instância \(([^)]+)\)|Instance type \(([^)]+)\)', config_text)
        # Buscar por todos os números de nós (português e inglês)
        nodes_counts = re.findall(r'Nós \((\d+)\)|Nodes \((\d+)\)', config_text)
        
        # Normalizar os resultados (pegar o grupo não vazio)
        instance_types = [match[0] or match[1] for match in instance_types]
        nodes_counts = [int(match[0] or match[1]) for match in nodes_counts]
        
        # Combinar tipos de instância com número de nós
        for i, instance_type in enumerate(instance_types):
            if i < len(nodes_counts):
                nodes = nodes_counts[i]
                # Pegar a instância com nós > 0 e que não seja r6gd.12xlarge
                if nodes > 0 and 'r6gd.12xlarge' not in instance_type:
                    details['tipo'] = instance_type
                    details['quantidade'] = nodes
                    break
        
        # Extrair opção de compra
        purchase_option = 'Reserved Instance'
        if 'OnDemand' in config_text:
            purchase_option = 'On Demand'
        elif 'Heavy Utilization' in config_text:
            purchase_option = 'Heavy Utilization'
        elif 'No Upfront' in config_text:
            purchase_option = 'No Upfront'
        elif 'All Upfront' in config_text:
            purchase_option = 'All Upfront'
        
        # Extrair período
        period = '1 ano'
        if '3 year' in config_text.lower() or '3-year' in config_text.lower():
            period = '3 anos'
        
        # Mecanismo de cache - buscar especificamente por Valkey, Memcached ou Redis
        cache_engine = 'Redis'  # padrão
        if 'Valkey' in config_text:
            cache_engine = 'Valkey'
        elif 'Memcached' in config_text:
            cache_engine = 'Memcached'
        
        details['specs'] = [purchase_option, period, cache_engine]
    
    elif "AWS Fargate" in service or "Fargate" in service:
        # Extrair número de tarefas/pods
        tasks_match = re.search(r'Número de tarefas ou pods \((\d+) por dia\)|Number of tasks or pods \((\d+) per day\)', config_text)
        if tasks_match:
            details['quantidade'] = int(tasks_match.group(1) if tasks_match.group(1) else tasks_match.group(2))
        else:
            # Fallback: buscar apenas o número
            fallback_match = re.search(r'(\d+) por dia', config_text)
            if fallback_match:
                details['quantidade'] = int(fallback_match.group(1))
        
        # Extrair vCPU
        vcpu_match = re.search(r'Quantidade de vCPU \(([\d.]+)\)|Amount of vCPU \(([\d.]+)\)', config_text)
        vcpu = vcpu_match.group(1) or vcpu_match.group(2) if vcpu_match else '0.25'
        
        # Extrair memória
        memory_match = re.search(r'Quantidade de memória alocada \((\d+) GB\)|Amount of memory allocated \((\d+) GB\)', config_text)
        memory = memory_match.group(1) or memory_match.group(2) if memory_match else '1'
        
        # Extrair arquitetura
        architecture = 'X86_64'
        if 'ARM' in config_text:
            architecture = 'ARM64'
        
        details['specs'] = [architecture]
    
    return details

def load_csv_file(file_path_or_buffer) -> pd.DataFrame:
    """Carrega o CSV lidando com a estrutura complexa do arquivo AWS"""
    if hasattr(file_path_or_buffer, 'read'):
        content = file_path_or_buffer.read().decode('utf-8-sig')
        lines = content.split('\n')
    else:
        with open(file_path_or_buffer, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
    
    # Encontrar o início da seção "Estimativa detalhada" ou "Detailed Estimate"
    start_idx = -1
    for i, line in enumerate(lines):
        if 'Estimativa detalhada' in line or 'Detailed Estimate' in line:
            start_idx = i + 1
            break
    
    if start_idx == -1:
        raise ValueError("Seção 'Estimativa detalhada' ou 'Detailed Estimate' não encontrada")
    
    # Encontrar o fim dos dados
    end_idx = len(lines)
    for i in range(start_idx + 1, len(lines)):
        if lines[i].strip() == '' or 'Confirmação' in lines[i] or 'Acknowledgement' in lines[i]:
            end_idx = i
            break
    
    # Extrair apenas as linhas de dados
    data_lines = lines[start_idx:end_idx]
    
    # Criar DataFrame
    from io import StringIO
    csv_data = '\n'.join(data_lines)
    df = pd.read_csv(StringIO(csv_data))
    
    return df

def process_csv(df: pd.DataFrame, lambda_payment_option: str = "No Upfront 12x pela AWS", fargate_payment_option: str = "No Upfront 12x pela AWS", global_payment_type: str = "All Upfront") -> Dict:
    """Processa o DataFrame e extrai informações relevantes"""
    result = {
        'client_name': '',
        'account_id': '',
        'services_by_region': defaultdict(lambda: defaultdict(list)),
        'regions': set()
    }
    
    # Extrair nome do cliente e ID da conta
    if not df.empty and 'Hierarquia de grupos' in df.columns:
        first_hierarchy = df['Hierarquia de grupos'].iloc[0]
        if ' > ' in first_hierarchy:
            client_account = first_hierarchy.split(' > ')[0].strip()
            
            if ' - ' in client_account:
                parts = client_account.split(' - ')
                if len(parts) >= 3:
                    result['client_name'] = ' - '.join(parts[:-1]).strip()
                    result['account_id'] = parts[-1].strip()
                elif len(parts) == 2:
                    result['client_name'] = parts[0].strip()
                    result['account_id'] = parts[1].strip()
            elif ' ' in client_account:
                client_parts = client_account.rsplit(' ', 1)
                result['client_name'] = client_parts[0].strip()
                result['account_id'] = client_parts[1].strip()
    
    # Processar todos os serviços
    for _, row in df.iterrows():
        region = row['Região']
        service = row['Serviço']
        upfront = float(row['Pagamento adiantado']) if pd.notna(row['Pagamento adiantado']) else 0
        monthly = float(row['Mensal']) if pd.notna(row['Mensal']) else 0
        config = row['Resumo da configuração']
        hierarchy = row['Hierarquia de grupos']
        
        result['regions'].add(region)
        
        # Determinar tipo de pagamento e custo
        payment_mode = 'No Upfront'
        total_cost = 0
        
        # Usar tipo de pagamento global para EC2, RDS e ElastiCache
        if ("EC2" in service or "RDS" in service or "Aurora" in service or "ElastiCache" in service):
            payment_mode = global_payment_type
            if payment_mode == 'All Upfront':
                total_cost = upfront if upfront > 0 else monthly
            else:
                total_cost = monthly if monthly > 0 else upfront
            
            # Correção especial para ElastiCache cache.t2.micro
            if "ElastiCache" in service and "cache.t2.micro" in config and payment_mode == 'All Upfront':
                payment_mode = 'Heavy Utilization'
        else:
            # Para outros serviços, manter lógica original
            if upfront > 0 and monthly == 0:
                payment_mode = 'All Upfront'
                total_cost = upfront
            elif upfront == 0 and monthly > 0:
                payment_mode = 'No Upfront'
                total_cost = monthly
            else:
                payment_mode = 'No Upfront'
                total_cost = monthly
        
        # Aplicar descontos específicos
        if "CloudFront" in service:
            payment_mode = 'No Upfront'
            # Garantir que usa o valor mensal correto e aplica 30% de desconto
            base_cost = monthly if monthly > 0 else upfront
            total_cost = base_cost * 0.7  # 30% desconto
        elif "AWS Lambda" in service or "Lambda" in service:
            # Lambda sempre processa (mesmo On Demand)
            payment_mode = 'All Upfront' if 'All Upfront' in lambda_payment_option else 'No Upfront'
            is_sao_paulo = 'São Paulo' in region or 'América do Sul' in region
            
            if payment_mode == 'All Upfront':
                base_cost = upfront if upfront > 0 else monthly
            else:
                base_cost = monthly
            
            if is_sao_paulo:
                if payment_mode == 'All Upfront':
                    total_cost = base_cost * 0.85  # 15% desconto
                else:
                    total_cost = base_cost * 0.90  # 10% desconto
            else:
                if payment_mode == 'All Upfront':
                    total_cost = base_cost * 0.83  # 17% desconto
                else:
                    total_cost = base_cost * 0.88  # 12% desconto
        elif "AWS Fargate" in service or "Fargate" in service:
            # Fargate sempre processa (mesmo On Demand)
            payment_mode = 'All Upfront' if 'All Upfront' in fargate_payment_option else 'No Upfront'
            is_arm = 'ARM' in config
            is_sao_paulo = 'São Paulo' in region or 'América do Sul' in region
            
            # Sempre usar o valor mensal como base para Fargate
            base_cost = monthly
            
            if is_sao_paulo:
                if payment_mode == 'All Upfront':
                    if is_arm:
                        total_cost = base_cost * 0.74  # 26% desconto
                    else:
                        total_cost = base_cost * 0.78  # 22% desconto
                else:
                    if is_arm:
                        total_cost = base_cost * 0.79  # 21% desconto
                    else:
                        total_cost = base_cost * 0.85  # 15% desconto
            else:
                if payment_mode == 'All Upfront':
                    if is_arm:
                        total_cost = base_cost * 0.73  # 27% desconto
                    else:
                        total_cost = base_cost * 0.73  # 27% desconto
                else:
                    if is_arm:
                        total_cost = base_cost * 0.79  # 21% desconto
                    else:
                        total_cost = base_cost * 0.80  # 20% desconto
        elif "RDS" in service or "Aurora" in service:
            # Aplicar desconto de armazenamento para RDS No Upfront
            if payment_mode == 'No Upfront':
                base_cost = monthly
                # Verificar se tem especificação de armazenamento (20 GB)
                if "Quantidade de armazenamento (20 GB)" in config:
                    is_sao_paulo = 'São Paulo' in region or 'América do Sul' in region
                    if is_sao_paulo:
                        total_cost = base_cost - 4.38  # Desconto São Paulo
                    else:
                        total_cost = base_cost - 2.3   # Desconto outras regiões
                else:
                    total_cost = base_cost
            else:
                total_cost = upfront
        else:
            # Para outros serviços, usar a lógica padrão
            if payment_mode == 'All Upfront':
                total_cost = upfront
            else:
                total_cost = monthly
        
        # Já tratado na lógica principal acima
        
        # Pular linhas On Demand (exceto Lambda, Fargate e CloudFront)
        if ('On-demand' in hierarchy or 'On Demand' in hierarchy or 'On-Demand' in hierarchy):
            # Permitir apenas Lambda, Fargate e CloudFront em On Demand
            if ('AWS Lambda' not in service and 'Lambda' not in service and 
                'AWS Fargate' not in service and 'Fargate' not in service and 
                'CloudFront' not in service):
                continue
        
        details = extract_instance_details(config, service)
        
        # Categorizar por serviço
        service_key = None
        if "EC2" in service:
            service_key = 'EC2'
        elif "RDS" in service or "Aurora" in service:
            service_key = 'RDS'
        elif "ElastiCache" in service:
            service_key = 'ElastiCache'
        elif "CloudFront" in service:
            service_key = 'CloudFront'
        elif "AWS Lambda" in service or "Lambda" in service:
            service_key = 'Lambda'
        elif "AWS Fargate" in service or "Fargate" in service:
            service_key = 'Fargate'
        
        if service_key:
            result['services_by_region'][region][service_key].append({
                'tipo': details.get('tipo', 'N/A'),
                'quantidade': details.get('quantidade', 1),
                'specs': details.get('specs', []),
                'payment_mode': payment_mode,
                'cost': total_cost,
                'upfront': upfront,
                'service_name': service,
                'config': config
            })
    
    return result

def calculate_on_demand_costs(df: pd.DataFrame) -> float:
    """Calcula o custo total On Demand anual"""
    on_demand_total = 0
    
    for _, row in df.iterrows():
        hierarchy = row['Hierarquia de grupos']
        monthly = float(row['Mensal']) if pd.notna(row['Mensal']) else 0
        
        # Identificar linhas On Demand
        if ('On-demand' in hierarchy or 'On Demand' in hierarchy or 'On-Demand' in hierarchy):
            on_demand_total += monthly * 12  # Converter para anual
    
    return on_demand_total

def generate_summary(data: Dict, exchange_rate: float, tax_rate: float = 13.83, lambda_payment_option: str = "No Upfront 12x pela AWS", fargate_payment_option: str = "No Upfront 12x pela AWS") -> str:
    """Gera o resumo formatado baseado nos modelos"""
    client_name = data['client_name']
    account_id = data['account_id']
    
    summary = f"Resumos dos recursos a serem reservados\n{client_name} - {account_id}\n\n"
    
    # Totais por tipo de pagamento
    total_no_upfront = 0
    total_all_upfront = 0
    total_serverless_no_upfront = 0
    total_serverless_all_upfront = 0
    total_database_no_upfront = 0
    total_database_all_upfront = 0
    
    # Processar por região
    for region in sorted(data['regions']):
        if region not in data['services_by_region']:
            continue
        
        # Mapear nome da região
        region_name = region
        if "N. da Virgínia" in region or "N. Virginia" in region or "Leste dos EUA" in region:
            region_name = "N. Virginia"
        elif "São Paulo" in region or "América do Sul" in region:
            region_name = "São Paulo"
        
        summary += f"{region_name}\n"
        
        services = data['services_by_region'][region]
        
        # Primeiro processar serviços tradicionais (EC2, ElastiCache, CloudFront)
        for service_type in ['EC2', 'ElastiCache', 'CloudFront']:
            if service_type not in services or not services[service_type]:
                continue
            
            instances = services[service_type]
            
            # Separar por tipo de pagamento
            no_upfront_instances = [i for i in instances if i['payment_mode'] == 'No Upfront']
            all_upfront_instances = [i for i in instances if i['payment_mode'] in ['All Upfront', 'Heavy Utilization']]
            
            # Calcular totais
            no_upfront_cost = sum(i['cost'] for i in no_upfront_instances)
            all_upfront_cost = sum(i['cost'] for i in all_upfront_instances)
            
            # Somar aos totais gerais (apenas serviços tradicionais)
            total_no_upfront += no_upfront_cost
            total_all_upfront += all_upfront_cost
            
            # Gerar seção do serviço
            if service_type == 'EC2':
                total_instances = sum(i['quantidade'] for i in instances)
                summary += f"EC2 Instances - {total_instances:02d} instâncias - Conta AWS {account_id}\n"
                summary += "Tipos de Instancias:\n"
                
                # Separar por tipo de pagamento
                no_upfront_grouped = {}
                all_upfront_grouped = {}
                
                for instance in instances:
                    pricing_strategy = instance['specs'][0] if len(instance['specs']) > 0 else 'N/A'
                    os_system = instance['specs'][1] if len(instance['specs']) > 1 else 'N/A'
                    key = f"{instance['tipo']} ({pricing_strategy}, {os_system})"
                    
                    if instance['payment_mode'] == 'No Upfront':
                        if key in no_upfront_grouped:
                            no_upfront_grouped[key] += instance['quantidade']
                        else:
                            no_upfront_grouped[key] = instance['quantidade']
                    else:
                        if key in all_upfront_grouped:
                            all_upfront_grouped[key] += instance['quantidade']
                        else:
                            all_upfront_grouped[key] = instance['quantidade']
                
                # Mostrar No Upfront
                if no_upfront_grouped:
                    summary += "No Upfront:\n"
                    for instance_key, total_qty in no_upfront_grouped.items():
                        summary += f"-{total_qty} - {instance_key}\n"
                
                # Mostrar All Upfront
                if all_upfront_grouped:
                    summary += "All Upfront:\n"
                    for instance_key, total_qty in all_upfront_grouped.items():
                        summary += f"-{total_qty} - {instance_key}\n"
                
                if no_upfront_cost > 0:
                    summary += f"Valor total No Upfront: USD {no_upfront_cost:,.2f}/mês\n"
                if all_upfront_cost > 0:
                    summary += f"Valor total All Upfront: USD {all_upfront_cost:,.2f}/ano\n"
            

            
            elif service_type == 'ElastiCache':
                total_nodes = sum(i['quantidade'] for i in instances)
                summary += f"ElastiCache - {total_nodes:02d} nós - Conta AWS {account_id}\n"
                summary += "Tipos de Instancias:\n"
                
                # Separar por tipo de pagamento
                no_upfront_grouped = {}
                all_upfront_grouped = {}
                
                for instance in instances:
                    period = instance['specs'][1] if len(instance['specs']) > 1 else 'N/A'
                    cache_engine = instance['specs'][2] if len(instance['specs']) > 2 else 'N/A'
                    key = f"{instance['tipo']} ({period}, {cache_engine})"
                    
                    if instance['payment_mode'] == 'No Upfront':
                        if key in no_upfront_grouped:
                            no_upfront_grouped[key] += instance['quantidade']
                        else:
                            no_upfront_grouped[key] = instance['quantidade']
                    else:
                        if key in all_upfront_grouped:
                            all_upfront_grouped[key] += instance['quantidade']
                        else:
                            all_upfront_grouped[key] = instance['quantidade']
                
                # Mostrar No Upfront
                if no_upfront_grouped:
                    summary += "No Upfront:\n"
                    for instance_key, total_qty in no_upfront_grouped.items():
                        summary += f"-{total_qty} - {instance_key}\n"
                
                # Mostrar All Upfront
                if all_upfront_grouped:
                    summary += "All Upfront:\n"
                    for instance_key, total_qty in all_upfront_grouped.items():
                        summary += f"-{total_qty} - {instance_key}\n"
                
                if no_upfront_cost > 0:
                    summary += f"Valor total No Upfront: USD {no_upfront_cost:,.2f}/mês\n"
                if all_upfront_cost > 0:
                    summary += f"Valor total All Upfront: USD {all_upfront_cost:,.2f}/ano\n"
            
            elif service_type == 'CloudFront':
                summary += f"CloudFront - Conta AWS {account_id}\n"
                summary += "Período: 1 ano\n"
                summary += "Forma de pagamento: No Upfront em 12x pela AWS\n"
                summary += f"Valor total mensal: USD {no_upfront_cost:,.2f} (sem impostos)\n"
            

            
            summary += "\n"
        
        # Processar Database Savings Plans (RDS/Aurora)
        if 'RDS' in services and services['RDS']:
            instances = services['RDS']
            
            # Separar por tipo de pagamento
            no_upfront_instances = [i for i in instances if i['payment_mode'] == 'No Upfront']
            all_upfront_instances = [i for i in instances if i['payment_mode'] in ['All Upfront', 'Heavy Utilization']]
            
            # Calcular totais
            no_upfront_cost = sum(i['cost'] for i in no_upfront_instances)
            all_upfront_cost = sum(i['cost'] for i in all_upfront_instances)
            
            # Somar aos totais database
            total_database_no_upfront += no_upfront_cost
            total_database_all_upfront += all_upfront_cost
            
            total_instances = sum(i['quantidade'] for i in instances)
            
            # Verificar se é Aurora (ACUs) ou RDS tradicional
            has_aurora = any('ACU' in str(i.get('config', '')) for i in instances)
            
            if has_aurora:
                summary += f"RDS/Aurora - {total_instances:02d} instâncias - Conta AWS {account_id}\n"
            else:
                summary += f"RDS - {total_instances:02d} instâncias - Conta AWS {account_id}\n"
            
            summary += "Tipos de Instancias:\n"
            
            # Separar por tipo de pagamento
            no_upfront_grouped = {}
            all_upfront_grouped = {}
            
            for instance in instances:
                az = instance['specs'][0] if len(instance['specs']) > 0 else 'N/A'
                period = instance['specs'][2] if len(instance['specs']) > 2 else 'N/A'
                engine = instance['specs'][3] if len(instance['specs']) > 3 else 'N/A'
                
                # Para Aurora, mostrar ACUs
                if 'ACU' in str(instance.get('config', '')):
                    # Extrair ACUs do config
                    import re
                    acu_match = re.search(r'(\d+)\s*ACU', str(instance.get('config', '')))
                    acus = acu_match.group(1) if acu_match else instance['tipo']
                    key = f"{acus}ACUs - ({az}, {period}, {engine})"
                else:
                    key = f"{instance['tipo']} - ({az}, {period}, {engine})"
                
                if instance['payment_mode'] == 'No Upfront':
                    if key in no_upfront_grouped:
                        no_upfront_grouped[key] += instance['quantidade']
                    else:
                        no_upfront_grouped[key] = instance['quantidade']
                else:
                    if key in all_upfront_grouped:
                        all_upfront_grouped[key] += instance['quantidade']
                    else:
                        all_upfront_grouped[key] = instance['quantidade']
            
            # Mostrar No Upfront
            if no_upfront_grouped:
                summary += "No Upfront:\n"
                for instance_key, total_qty in no_upfront_grouped.items():
                    summary += f"-{total_qty} - {instance_key}\n"
            
            # Mostrar All Upfront
            if all_upfront_grouped:
                summary += "All Upfront:\n"
                for instance_key, total_qty in all_upfront_grouped.items():
                    summary += f"-{total_qty} - {instance_key}\n"
            
            if no_upfront_cost > 0:
                summary += f"Valor total No Upfront: USD {no_upfront_cost:,.2f}/mês\n"
            if all_upfront_cost > 0:
                summary += f"Valor total All Upfront: USD {all_upfront_cost:,.2f}/ano\n"
            
            summary += "\n"
        
        # Agora processar serviços serverless separadamente
        serverless_services = ['Lambda', 'Fargate']
        for service_type in serverless_services:
            if service_type not in services or not services[service_type]:
                continue
            
            instances = services[service_type]
            
            # Separar por tipo de pagamento
            no_upfront_instances = [i for i in instances if i['payment_mode'] == 'No Upfront']
            all_upfront_instances = [i for i in instances if i['payment_mode'] in ['All Upfront', 'Heavy Utilization']]
            
            # Calcular totais
            no_upfront_cost = sum(i['cost'] for i in no_upfront_instances)
            all_upfront_cost = sum(i['cost'] for i in all_upfront_instances)
            
            # Somar aos totais serverless
            total_serverless_no_upfront += no_upfront_cost
            total_serverless_all_upfront += all_upfront_cost * 12  # Multiplicar por 12 para serverless
            
            if service_type == 'Lambda':
                summary += f"Lambda - Conta AWS {account_id}\n"
                summary += f"Forma de pagamento: {lambda_payment_option}\n"
                if no_upfront_cost > 0:
                    summary += f"Valor total No Upfront: USD {no_upfront_cost:,.2f}/mês\n"
                if all_upfront_cost > 0:
                    summary += f"Valor total All Upfront: USD {all_upfront_cost * 12:,.2f}/ano\n"
            
            elif service_type == 'Fargate':
                total_tasks = sum(i['quantidade'] for i in instances)
                summary += f"ECS fargate - {region_name} - Conta AWS {account_id}\n"
                summary += "Período: 1 ano\n"
                summary += f"Forma de pagamento: {fargate_payment_option}\n"
                summary += f"Total de tarefas/pods: {total_tasks}\n"
                
                if no_upfront_cost > 0:
                    summary += f"Valor total No Upfront: USD {no_upfront_cost:,.2f}/mês\n"
                if all_upfront_cost > 0:
                    summary += f"Valor total All Upfront: USD {all_upfront_cost * 12:,.2f}/ano\n"
            
            summary += "\n"
    
    # Resumo financeiro para serviços tradicionais (EC2, ElastiCache, CloudFront)
    if total_all_upfront > 0:
        summary += "Resumo financeiro All Upfront:\n"
        all_upfront_taxes = total_all_upfront * (tax_rate / 100)
        all_upfront_with_taxes = total_all_upfront + all_upfront_taxes
        all_upfront_brl = all_upfront_with_taxes * exchange_rate
        all_upfront_parcela = all_upfront_brl / 6
        
        summary += f"Valor total (sem imposto): USD {total_all_upfront:,.2f}/ano\n"
        summary += f"Impostos: USD {all_upfront_taxes:,.2f}/ano\n"
        summary += f"Valor do dólar (aproximado): R$ {exchange_rate:.2f}\n"
        summary += f"Valor total em reais (com imposto): R$ {all_upfront_brl:,.2f}/ano\n"
        summary += f"Parcelamento TdSynnex(com imposto): 06x R$ {all_upfront_parcela:,.2f} via TdSynnex\n\n"
    
    if total_no_upfront > 0:
        summary += "Resumo financeiro No Upfront:\n"
        no_upfront_annual = total_no_upfront * 12
        no_upfront_taxes = no_upfront_annual * (tax_rate / 100)
        no_upfront_with_taxes = no_upfront_annual + no_upfront_taxes
        no_upfront_brl_monthly = no_upfront_with_taxes * exchange_rate / 12
        
        summary += f"Valor total (sem imposto): USD {no_upfront_annual:,.2f}/ano\n"
        summary += f"Impostos: USD {no_upfront_taxes:,.2f}/ano\n"
        summary += f"Valor do dólar (aproximado): R$ {exchange_rate:.2f}\n"
        summary += f"Valor total em reais (com imposto): 12x R$ {no_upfront_brl_monthly:,.2f} via AWS\n\n"
    
    # Resumo financeiro para Database Savings Plans (RDS/Aurora)
    if total_database_all_upfront > 0:
        summary += "Resumo financeiro Database All Upfront:\n"
        database_all_upfront_taxes = total_database_all_upfront * (tax_rate / 100)
        database_all_upfront_with_taxes = total_database_all_upfront + database_all_upfront_taxes
        database_all_upfront_brl = database_all_upfront_with_taxes * exchange_rate
        database_all_upfront_parcela = database_all_upfront_brl / 6
        
        summary += f"Valor total (sem imposto): USD {total_database_all_upfront:,.2f}/ano\n"
        summary += f"Impostos: USD {database_all_upfront_taxes:,.2f}/ano\n"
        summary += f"Valor do dólar (aproximado): R$ {exchange_rate:.2f}\n"
        summary += f"Valor total em reais (com imposto): R$ {database_all_upfront_brl:,.2f}/ano\n"
        summary += f"Parcelamento TdSynnex(com imposto): 06x R$ {database_all_upfront_parcela:,.2f} via TdSynnex\n\n"
    
    if total_database_no_upfront > 0:
        summary += "Resumo financeiro Database No Upfront:\n"
        database_no_upfront_annual = total_database_no_upfront * 12
        database_no_upfront_taxes = database_no_upfront_annual * (tax_rate / 100)
        database_no_upfront_with_taxes = database_no_upfront_annual + database_no_upfront_taxes
        database_no_upfront_brl_monthly = database_no_upfront_with_taxes * exchange_rate / 12
        
        summary += f"Valor total (sem imposto): USD {database_no_upfront_annual:,.2f}/ano\n"
        summary += f"Impostos: USD {database_no_upfront_taxes:,.2f}/ano\n"
        summary += f"Valor do dólar (aproximado): R$ {exchange_rate:.2f}\n"
        summary += f"Valor total em reais (com imposto): 12x R$ {database_no_upfront_brl_monthly:,.2f} via AWS\n\n"
    
    # Resumo financeiro para serviços serverless
    if total_serverless_all_upfront > 0:
        summary += "Resumo financeiro Serverless All Upfront:\n"
        serverless_all_upfront_taxes = total_serverless_all_upfront * (tax_rate / 100)
        serverless_all_upfront_with_taxes = total_serverless_all_upfront + serverless_all_upfront_taxes
        serverless_all_upfront_brl = serverless_all_upfront_with_taxes * exchange_rate
        serverless_all_upfront_parcela = serverless_all_upfront_brl / 6
        
        summary += f"Valor total (sem imposto): USD {total_serverless_all_upfront:,.2f}/ano\n"
        summary += f"Impostos: USD {serverless_all_upfront_taxes:,.2f}/ano\n"
        summary += f"Valor do dólar (aproximado): R$ {exchange_rate:.2f}\n"
        summary += f"Valor total em reais (com imposto): R$ {serverless_all_upfront_brl:,.2f}/ano\n"
        summary += f"Parcelamento TdSynnex(com imposto): 06x R$ {serverless_all_upfront_parcela:,.2f} via TdSynnex\n\n"
    
    if total_serverless_no_upfront > 0:
        summary += "Resumo financeiro Serverless No Upfront:\n"
        serverless_no_upfront_annual = total_serverless_no_upfront * 12
        serverless_no_upfront_taxes = serverless_no_upfront_annual * (tax_rate / 100)
        serverless_no_upfront_with_taxes = serverless_no_upfront_annual + serverless_no_upfront_taxes
        serverless_no_upfront_brl_monthly = serverless_no_upfront_with_taxes * exchange_rate / 12
        
        summary += f"Valor total (sem imposto): USD {serverless_no_upfront_annual:,.2f}/ano\n"
        summary += f"Impostos: USD {serverless_no_upfront_taxes:,.2f}/ano\n"
        summary += f"Valor do dólar (aproximado): R$ {exchange_rate:.2f}\n"
        summary += f"Valor total em reais (com imposto): 12x R$ {serverless_no_upfront_brl_monthly:,.2f} via AWS\n"
    
    return summary

def main():
    st.title("🏦 Resumo de Custos AWS - Savings Plans")
    st.markdown("""
    Esta aplicação processa arquivos CSV exportados da **Calculadora de Preços da AWS** 
    e gera resumos formatados de custos de reservas (Savings Plans).
    """)
    
    # Sidebar com configurações
    st.sidebar.header("⚙️ Configurações")
    exchange_rate = st.sidebar.number_input(
        "Taxa de câmbio USD para BRL", 
        value=5.50, 
        min_value=1.0, 
        step=0.01,
        help="Taxa de conversão do dólar americano para real brasileiro"
    )
    
    tax_rate = st.sidebar.number_input(
        "Taxa de Imposto (%)", 
        value=13.83, 
        min_value=0.0, 
        max_value=100.0,
        step=0.01,
        help="Taxa de imposto aplicada sobre o valor total"
    )
    
    lambda_payment_option = st.sidebar.selectbox(
        "Forma de pagamento Lambda",
        ["No Upfront 12x pela AWS", "All Upfront 06x pela TdSynnex"],
        help="Selecione a forma de pagamento específica para Lambda"
    )
    
    fargate_payment_option = st.sidebar.selectbox(
        "Forma de pagamento ECS Fargate",
        ["No Upfront 12x pela AWS", "All Upfront 06x pela TdSynnex"],
        help="Selecione a forma de pagamento específica para ECS Fargate"
    )
    
    # Opção global de tipo de pagamento
    global_payment_type = st.sidebar.selectbox(
        "Tipo de pagamento para EC2/RDS/ElastiCache",
        ["All Upfront", "No Upfront"],
        help="Força todos os serviços EC2, RDS e ElastiCache para este tipo de pagamento"
    )
    
    # Upload do arquivo
    st.header("📁 Upload do Arquivo")
    uploaded_file = st.file_uploader(
        "Escolha um arquivo CSV da Calculadora AWS", 
        type="csv",
        help="Faça upload do arquivo CSV exportado da Calculadora de Preços da AWS"
    )
    
    if uploaded_file is not None:
        try:
            # Ler CSV
            df = load_csv_file(uploaded_file)
            
            # Verificar se tem as colunas necessárias
            required_columns_pt = ['Hierarquia de grupos', 'Região', 'Serviço', 'Pagamento adiantado', 'Mensal', 'Resumo da configuração']
            required_columns_en = ['Group hierarchy', 'Region', 'Service', 'Upfront', 'Monthly', 'Configuration summary']
            
            is_portuguese = all(col in df.columns for col in required_columns_pt)
            is_english = all(col in df.columns for col in required_columns_en)
            
            if not is_portuguese and not is_english:
                missing_pt = [col for col in required_columns_pt if col not in df.columns]
                missing_en = [col for col in required_columns_en if col not in df.columns]
                st.error(f"Colunas faltando no CSV. Português: {', '.join(missing_pt)} | Inglês: {', '.join(missing_en)}")
                return
            
            # Normalizar nomes das colunas para português
            if is_english:
                column_mapping = {
                    'Group hierarchy': 'Hierarquia de grupos',
                    'Region': 'Região',
                    'Service': 'Serviço',
                    'Upfront': 'Pagamento adiantado',
                    'Monthly': 'Mensal',
                    'Configuration summary': 'Resumo da configuração'
                }
                df = df.rename(columns=column_mapping)
            
            # Processar dados
            data = process_csv(df, lambda_payment_option, fargate_payment_option, global_payment_type)
            
            if not data['account_id']:
                st.warning("Não foi possível extrair o ID da conta AWS do arquivo")
            
            # Calcular custos On Demand
            on_demand_cost = calculate_on_demand_costs(df)
            
            # Calcular totais para comparação (usando mesma lógica da generate_summary)
            total_no_upfront = 0
            total_all_upfront = 0
            total_serverless_no_upfront = 0
            total_serverless_all_upfront = 0
            total_database_no_upfront = 0
            total_database_all_upfront = 0
            
            for region_services in data['services_by_region'].values():
                for service_type, instances in region_services.items():
                    no_upfront_instances = [i for i in instances if i['payment_mode'] == 'No Upfront']
                    all_upfront_instances = [i for i in instances if i['payment_mode'] in ['All Upfront', 'Heavy Utilization']]
                    
                    no_upfront_cost = sum(i['cost'] for i in no_upfront_instances)
                    all_upfront_cost = sum(i['cost'] for i in all_upfront_instances)
                    
                    # Separar por categoria
                    if service_type in ['Lambda', 'Fargate']:
                        total_serverless_no_upfront += no_upfront_cost
                        total_serverless_all_upfront += all_upfront_cost * 12
                    elif service_type == 'RDS':
                        total_database_no_upfront += no_upfront_cost
                        total_database_all_upfront += all_upfront_cost
                    else:
                        total_no_upfront += no_upfront_cost
                        total_all_upfront += all_upfront_cost
            
            # Converter No Upfront para anual
            total_no_upfront_annual = total_no_upfront * 12
            total_serverless_no_upfront_annual = total_serverless_no_upfront * 12
            total_database_no_upfront_annual = total_database_no_upfront * 12
            
            # Totais combinados
            combined_no_upfront = total_no_upfront_annual + total_serverless_no_upfront_annual + total_database_no_upfront_annual
            combined_all_upfront = total_all_upfront + total_serverless_all_upfront + total_database_all_upfront
            
            # Tabela de comparação de custos
            st.header("💰 Comparação de Custos")
            
            # Criar DataFrame para a tabela
            comparison_data = {
                'Tipo de Pagamento': ['On Demand', 'No Upfront (Compute)', 'All Upfront (Compute)', 'No Upfront (Database)', 'All Upfront (Database)', 'No Upfront (Serverless)', 'All Upfront (Serverless)', 'Total No Upfront', 'Total All Upfront'],
                'Custo Anual (USD)': [
                    f"${on_demand_cost:,.2f}",
                    f"${total_no_upfront_annual:,.2f}" if total_no_upfront_annual > 0 else "$0.00",
                    f"${total_all_upfront:,.2f}" if total_all_upfront > 0 else "$0.00",
                    f"${total_database_no_upfront_annual:,.2f}" if total_database_no_upfront_annual > 0 else "$0.00",
                    f"${total_database_all_upfront:,.2f}" if total_database_all_upfront > 0 else "$0.00",
                    f"${total_serverless_no_upfront_annual:,.2f}" if total_serverless_no_upfront_annual > 0 else "$0.00",
                    f"${total_serverless_all_upfront:,.2f}" if total_serverless_all_upfront > 0 else "$0.00",
                    f"${combined_no_upfront:,.2f}" if combined_no_upfront > 0 else "$0.00",
                    f"${combined_all_upfront:,.2f}" if combined_all_upfront > 0 else "$0.00"
                ],
                'Economia vs On Demand': ['0%', '', '', '', '', '', '', '', '']
            }
            
            # Calcular economias
            if on_demand_cost > 0:
                if total_no_upfront_annual > 0:
                    no_upfront_savings = ((on_demand_cost - total_no_upfront_annual) / on_demand_cost) * 100
                    comparison_data['Economia vs On Demand'][1] = f"{no_upfront_savings:.1f}%"
                
                if total_all_upfront > 0:
                    all_upfront_savings = ((on_demand_cost - total_all_upfront) / on_demand_cost) * 100
                    comparison_data['Economia vs On Demand'][2] = f"{all_upfront_savings:.1f}%"
                
                if total_database_no_upfront_annual > 0:
                    database_no_upfront_savings = ((on_demand_cost - total_database_no_upfront_annual) / on_demand_cost) * 100
                    comparison_data['Economia vs On Demand'][3] = f"{database_no_upfront_savings:.1f}%"
                
                if total_database_all_upfront > 0:
                    database_all_upfront_savings = ((on_demand_cost - total_database_all_upfront) / on_demand_cost) * 100
                    comparison_data['Economia vs On Demand'][4] = f"{database_all_upfront_savings:.1f}%"
                
                if total_serverless_no_upfront_annual > 0:
                    serverless_no_upfront_savings = ((on_demand_cost - total_serverless_no_upfront_annual) / on_demand_cost) * 100
                    comparison_data['Economia vs On Demand'][5] = f"{serverless_no_upfront_savings:.1f}%"
                
                if total_serverless_all_upfront > 0:
                    serverless_all_upfront_savings = ((on_demand_cost - total_serverless_all_upfront) / on_demand_cost) * 100
                    comparison_data['Economia vs On Demand'][6] = f"{serverless_all_upfront_savings:.1f}%"
                
                if combined_no_upfront > 0:
                    combined_no_upfront_savings = ((on_demand_cost - combined_no_upfront) / on_demand_cost) * 100
                    comparison_data['Economia vs On Demand'][7] = f"{combined_no_upfront_savings:.1f}%"
                
                if combined_all_upfront > 0:
                    combined_all_upfront_savings = ((on_demand_cost - combined_all_upfront) / on_demand_cost) * 100
                    comparison_data['Economia vs On Demand'][8] = f"{combined_all_upfront_savings:.1f}%"
            
            # Exibir tabela
            comparison_df = pd.DataFrame(comparison_data)
            st.dataframe(comparison_df, use_container_width=True, hide_index=True)
            
            # Gerar resumo
            summary = generate_summary(data, exchange_rate, tax_rate, lambda_payment_option, fargate_payment_option)
            
            # Exibir resumo
            st.header("📋 Resumo Gerado")
            st.success("✅ Arquivo processado com sucesso!")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.text_area(
                    "Resumo dos Custos", 
                    value=summary, 
                    height=600,
                    help="Copie este texto ou faça o download usando o botão ao lado"
                )
            
            with col2:
                st.download_button(
                    label="📥 Download do Resumo",
                    data=summary,
                    file_name=f"resumo_aws_{data['client_name']}_{data['account_id']}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
                
                # Estatísticas rápidas
                total_instances = sum(len(instances) for region_services in data['services_by_region'].values() for instances in region_services.values())
                st.metric("Total Regiões", f"{len(data['regions'])}")
                st.metric("Total Serviços", f"{total_instances}")
                
                # Mostrar economia principal
                if on_demand_cost > 0 and combined_all_upfront > 0:
                    main_savings = ((on_demand_cost - combined_all_upfront) / on_demand_cost) * 100
                    st.metric("Economia All Upfront", f"{main_savings:.1f}%")
            
            # Mostrar dados processados (debug)
            with st.expander("🔍 Dados Processados (Debug)"):
                st.json(data)
                st.write(f"On Demand Total: ${on_demand_cost:,.2f}")
                st.write(f"No Upfront Compute: ${total_no_upfront_annual:,.2f}")
                st.write(f"All Upfront Compute: ${total_all_upfront:,.2f}")
                st.write(f"No Upfront Database: ${total_database_no_upfront_annual:,.2f}")
                st.write(f"All Upfront Database: ${total_database_all_upfront:,.2f}")
                st.write(f"No Upfront Serverless: ${total_serverless_no_upfront_annual:,.2f}")
                st.write(f"All Upfront Serverless: ${total_serverless_all_upfront:,.2f}")
                st.write(f"Total No Upfront: ${combined_no_upfront:,.2f}")
                st.write(f"Total All Upfront: ${combined_all_upfront:,.2f}")
                
        except Exception as e:
            st.error(f"Erro ao processar arquivo: {str(e)}")

if __name__ == "__main__":
    main()