
def get_grave():
    """Retorna o conteúdo de 'Evitar a todo custo'"""
    return {'Exclusão da Garantia de Evicção': 'Se o contrato tentar excluir a garantia legal de evicção de forma total, o comprador corre o risco de perder o imóvel para um terceiro que o reivindique na justiça, ficando sem o bem e sem o direito a ressarcimento.', 'Procurações Embutidas com Poderes Amplos': 'O contrato não deve conter procurações que deem à outra parte poderes amplos para atuar em seu nome de forma prejudicial. Procurações irrevogáveis só são válidas se estiverem vinculadas a uma obrigação contratual e devem se restringir a atos específicos.', 'Ausência de Condição Suspensiva para Financiamento': 'Se a compra depende de crédito, a ausência dessa cláusula significa que uma negativa do banco não libera o comprador, fazendo com que ele responda por inadimplemento e corra o risco de perder o sinal.', 'Solidariedade Implícita': 'Se houver mais de um comprador, a responsabilidade solidária permite que o vendedor cobre o valor integral de apenas um deles, obrigando-o a arcar com a cota do parceiro inadimplente.', 'Garantias Defeituosas ou Ilíquidas': 'Verificar se o contrato prevê garantias adequadas e a exigência de averbação da caução real na matrícula. Uma garantia não averbada é inútil em caso de insolvência.', 'Falta de Due Diligence Mencionada': "Se o contrato não citar a realização de uma auditoria prévia (certidões negativas, passivos trabalhistas, zoneamento), resulta na aquisição de 'ativos tóxicos'.", 'Dupla Garantia Locatícia': 'Exigência de fiador e caução no mesmo contrato é nula e configura contravenção penal (Lei do Inquilinato). Uma delas deve ser removida imediatamente.', 'Multa por Rescisão Não Proporcional': "A lei obriga que a multa seja proporcional ao tempo não cumprido. Multas fixas (ex: '3 aluguéis') sem proporcionalidade serão anuladas em juízo.", 'Repasse de Vícios Estruturais': 'O dever de sanar vícios estruturais (rachaduras, infiltrações preexistentes) é intransferível e pertence ao proprietário.'}

def get_media():
    """Retorna o conteúdo de 'Cláusulas perigosas e abusivas'"""
    return {'Multas Unilaterais e Exageradas (Cláusula Penal)': 'Comum em contratos de vendedores. Sugestão: Tornar a penalidade bilateral e limitar a multa entre 10% e 20%.', 'Responsabilidade Antecipada por Encargos': 'Forçar o comprador a pagar IPTU e condomínio antes de receber as chaves. Solução: Condicionar o pagamento apenas à data de entrega e laudo de vistoria.', 'Foro de Eleição e Arbitragem Desproporcionais': 'Eleger foro distante ou arbitragem custosa para inviabilizar resoluções. Sugestão: Recomendar o foro da situação do imóvel ou do domicílio do comprador.', "Cláusula de 'Aceitação Plena'": 'Tenta afastar reclamações sobre vícios ocultos. Alerta: O prazo legal para reclamar de vícios ocultos é de 1 ano, e a cláusula não exime o vendedor de defeitos graves.', 'Multas Moratórias Assimétricas no Atraso': 'Punição severa para o comprador mas inexistente para a construtora que atrasa a obra. Sugestão: Reequilibrar para garantir lucros cessantes.'}

def get_faltantes():
    """Retorna o conteúdo de 'Informações Faltantes e Omissões'"""
    return {'Descrição Genérica do Objeto': 'A descrição deve reproduzir fielmente a matrícula. Se vagas, depósitos e móveis não estiverem listados, podem ser excluídos pelo vendedor.', 'Prazo para Escritura e Registro': 'A omissão de data objetiva permite ao vendedor adiar a lavratura, deixando o comprador vulnerável a penhoras ou vendas a terceiros.', 'Isenção de Débitos Anteriores': 'Faltar a declaração de entrega livre de débitos fiscais/condominiais é um risco. Dívidas propter rem podem recair sobre o comprador.', 'Restrição na Cessão de Direitos': "Ausência de regras claras para repassar o negócio antes da escritura pode 'travar' o comprador.", 'Omissões na Rescisão Antecipada': 'Verificar se existe cláusula de rescisão com gradação de penalidades e rito claro de notificação prévia.'}

if __name__ == "__main__":
    print("--- ANÁLISE DE RISCO CONTRATUAL ---")
    
    print("\n[GRAVE - Evitar a Todo Custo]")
    for item, desc in get_grave().items():
        print(f" - {item}: {desc}")
        
    print("\n[MÉDIA - Cláusulas Perigosas/Abusivas]")
    for item, desc in get_media().items():
        print(f" - {item}: {desc}")
        
    print("\n[FALTANTES - Informações Faltantes e Omissões]")
    for item, desc in get_faltantes().items():
        print(f" - {item}: {desc}")
