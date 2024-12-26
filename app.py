from flask import Flask, request, render_template
from flask import Flask, render_template, send_from_directory, request, redirect, url_for, Response, jsonify
import os
from zipfile import ZipFile
import shutil
import subprocess
from werkzeug.utils import secure_filename
import pandas as pd
import numpy as np
import time
from datetime import datetime
import traceback

app = Flask(__name__)


app.config['MAX_CONTENT_LENGTH'] = None
nomepasta = None
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# backup Local


global df_stage_merge




@app.route('/semretencao', methods=['GET'])
def semretencao():
    print("semretencao")

    # Obter o parâmetro `id` da URL, que contém NR_OS e TREM
    OSfilters = request.args.get('id')
    if OSfilters:
        # Divide o parâmetro em NR_OS e TREM usando a vírgula
        OSfilters = OSfilters.split(',')
        if len(OSfilters) == 2:
            nr_os = OSfilters[0].strip()  # NR_OS
            trem = OSfilters[1].strip()  # TREM

            print(f"NR_OS: {nr_os}, TREM: {trem}")
        else:
            print("Parâmetro 'id' não contém valores válidos para NR_OS e TREM.")
            return "Erro: Parâmetro 'id' inválido", 400
    else:
        print("Parâmetro 'id' não encontrado na URL.")
        return "Erro: Parâmetro 'id' não encontrado", 400

    # Processamento do DataFrame
    geralCards = pd.read_csv('files//submitted_data.csv')
    
    # Obter data e hora atual
    data_atual = datetime.now()

    # Criar uma nova linha para o DataFrame
# Criar uma nova linha para o DataFrame
    new_row = pd.DataFrame({'NR_OS': [nr_os], 'TREM': [trem], 'ATIVO_TL': ["Sem Retencões"]})
    new_row['data_now'] = data_atual

    new_row['ID'] = data_atual.strftime('%Y%m%d%H%M%S')  # Formatar como string de ID
    new_row['data_now'] = new_row['data_now'].dt.strftime('%d/%m/%Y %H:%M:%S')


    # Concatenar a nova linha ao DataFrame
    geralCards = pd.concat([new_row, geralCards], ignore_index=True)
    print(geralCards.head(5))

    # Salvar o DataFrame atualizado de volta no arquivo CSV
    geralCards.to_csv('files//submitted_data.csv', index=False)

    # Redirecionar para outra rota
    return redirect(url_for('cardsGeral'))


@app.route('/delete_item/<int:id>', methods=['POST'])
def delete_item(id):
    print("Excluir")

    geralCards = pd.read_csv('files//submitted_data.csv')
    print(geralCards.head(5))
    # Filtra o DataFrame removendo o item pelo ID
    geralCards = geralCards[geralCards['NR_OS'] != id]

    geralCards.to_csv('files//submitted_data.csv', index=False)

    return redirect(url_for('cardsGeral'))


@app.route('/salvar-df', methods=['POST'])
def salvar_df():
    try:
        # Recebe os dados JSON do request
        data = request.get_json()
        rows = data.get('data', [])

        if not rows:
            return jsonify({"message": "Nenhuma linha recebida."}), 400

        # Converte para DataFrame
        columns = [
            "Reter", "VAGAO", "SERIE", "TREM", "SEQUENCIA", "LOCAL", "ORIGEM",
            "DESTINO", "NR_OS", "ATIVO_TL", "DESC_LOTACAO" ,"NOTA", "DT_NOTA", "Notificador",
            "Texto_Causa", "TP_NOTA", "TEXTO", "Texto_Item", "Texto_AVARIA",
            "DATA_QMDAT", "CodFalha", "Flag", "Aux_Status", "BASE", 'Qtd_vg_Por_OS','nt_critica'
        ]
        df = pd.DataFrame(rows, columns=columns)

        # Salvar em arquivo local (opcional)
        df.to_csv('files//tempoary_df.csv', index=False)

        return redirect(url_for('sucesso'))

    except Exception as e:
        # Captura o erro e imprime o traceback completo para depuração
        error_details = traceback.format_exc()
        print(f"Erro detalhado: {error_details}")

        return jsonify({
            "message": "Erro ao processar os dados.",
            "error": str(e),
            "details": error_details
        }), 500


@app.route('/submit', methods=['POST'])
def submit():
    # Dados enviados pelo formulário
    selected_data = request.json  # JSON recebido

    # Organizar os dados no formato adequado para criar um DataFrame
    processed_data = []
    for item in selected_data:
        processed_data.append({
            'NR_OS': item.get('NR_OS'),
            'TREM': item.get('TREM'),
            'ATIVO_TL': item.get('ATIVO_TL'),
            'DESC_LOTACAO': item.get('DESC_LOTACAO'),
            'NOTA': item.get('NOTA'),
            'Pode_ir_para_TOM': item.get('Pode_ir_para_TOM'),
            'Obrigatoria': item.get('Obrigatoria'),
            'Local_Retencao': item.get('Local_Retencao'),
            'Isolado': item.get('Isolado'),
            'Rec_Sistema': item.get('Rec_Sistema'),
            'Sequencia': item.get('Sequencia'),
            'DT_NOTA': item.get('DT_NOTA'),
            'TEXTO': item.get('TEXTO'),
            'Texto_Causa': item.get('Texto_Causa'),
            'TP_NOTA': item.get('TP_NOTA'),
            'Local': item.get('Local_Retencao'),
            'Observacao_Retencao' : item.get('Observacao'),
            'Qtd_vg_Por_OS' : item.get('Qtd_vg_Por_OS'),
            'DataHoraPassagem': item.get('DataHoraPassagem')  # 1515
        })

    # Criar um DataFrame com os dados processados
    df_submitted = pd.DataFrame(processed_data)
    df_submitted['DataHoraPassagem'] = pd.to_datetime(df_submitted['DataHoraPassagem'])
    df_submitted['DataHoraPassagem'] = df_submitted['DataHoraPassagem'].dt.strftime('%d/%m/%Y %H:%M')


    df_submitted_OLD = pd.read_csv('files//submitted_data.csv')
    data_atual = datetime.now()
    data_atual = data_atual.strftime("%d/%m/%Y %H:%M:%S")
    df_submitted = df_submitted.fillna(' ')
    df_submitted = df_submitted.replace('NaN', ' ')

    df_submitted['data_now'] = data_atual
    df_submitted['data_now'] = data_atual
    df_submitted['data_now2'] = pd.to_datetime(
        df_submitted['data_now'],
        format='%d/%m/%Y %H:%M:%S',
        errors='coerce'
    )


    # Criar um DataFrame com os dados processados
    df_submitted = pd.DataFrame(processed_data)
    df_submitted['DataHoraPassagem'] = pd.to_datetime(df_submitted['DataHoraPassagem'])
    df_submitted['DataHoraPassagem'] = df_submitted['DataHoraPassagem'].dt.strftime('%d/%m/%Y %H:%M')
    #df_submitted = df_submitted['Sequencia'].astype(int).astype(str)

    # Carregar o DataFrame antigo
    df_submitted_OLD = pd.read_csv('files//submitted_data.csv')
    
    # Obter a data e hora atual
    data_atual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    # Substituir valores NaN por espaços em branco
    df_submitted = df_submitted.fillna(' ')
    df_submitted = df_submitted.replace('NaN', ' ')

    # Adicionar as colunas de data atual
    df_submitted['data_now'] = data_atual
    df_submitted['data_now2'] = pd.to_datetime(df_submitted['data_now'], format='%d/%m/%Y %H:%M:%S', errors='coerce')

    # Criar a nova coluna ID com a formatação desejada
    df_submitted['ID'] = df_submitted['data_now2'].dt.strftime('%Y%m%d%H%M%S')

    # Agora inicialize a variável 'result' corretamente
    result = df_submitted.copy()  # Inicializando 'result' com os dados de df_submitted

    # Ajustar 'NR_OS' e 'NOTA' para os formatos desejados
# Garantir que 'NR_OS' e 'NOTA' sejam convertidos corretamente
    if 'NR_OS' in result.columns:
        result['NR_OS'] = pd.to_numeric(result['NR_OS'], errors='coerce').fillna(0).astype(int).astype(str)

    if 'NOTA' in result.columns:
        result['NOTA'] = pd.to_numeric(result['NOTA'], errors='coerce').fillna(0).astype(int).astype(str)

    # Concatenar com o DataFrame antigo, mantendo apenas as linhas únicas com base em 'NOTA'
    result = pd.concat([df_submitted, df_submitted_OLD])
    result = result.drop_duplicates(subset=['NOTA'])

    # Exibir as primeiras 5 linhas para verificação
    print(result.head(5))

    # Salvar o DataFrame result em um arquivo CSV
    result.to_csv('files//submitted_data.csv', index=False)

    return redirect(url_for('cardsGeral'))


@app.route('/email')
def email():
    print("email")
    # Carregar o arquivo CSV
    geralCards = pd.read_csv('files//submitted_data.csv')
    geralCards = geralCards.replace('nao', 'NÃO')
    geralCards = geralCards.replace('sim', 'SIM')
    geralCards['Sequencia'] = geralCards['Sequencia'].fillna(0).astype(float).astype(int)
    geralCards = geralCards.drop_duplicates(
    subset=['NOTA'], keep='last')
    #



    # Filtrar apenas as linhas com TP_NOTA == 'M2'
    geralCards_Email = geralCards[
        (geralCards['TP_NOTA'].isin(['M2', 'M9', 'M6'])) | 
        (geralCards['Observacao_Retencao'].notna()) |
        (geralCards['ATIVO_TL'] == 'Sem Retencões') 
    ]
    geralCards = geralCards['Sequencia'].astype(int).astype(str)


    # Obter o parâmetro `id` da URL e converter para uma lista
    OSfilters = request.args.get('id')  # Exemplo: "1989210,1989564"
    if OSfilters:
        OSfilters = OSfilters.split(',')  # ["1989210", "1989564"]
        OSfilters = [int(id.strip())
                     for id in OSfilters]  # Convertendo para inteiros
    print("OSfilters")   
    
    print(OSfilters)
        

    # Filtrando o DataFrame com os IDs fornecidos
    geralCards_Email = geralCards_Email[geralCards_Email['NR_OS'].isin(
        OSfilters)]

    geralCards_Email['Defeitos'] = geralCards_Email['TEXTO'].fillna("").astype(str) + \
        " " + geralCards_Email['Texto_Causa'].fillna("").astype(str)

    # Agrupar por 'NR_OS' e concatenar os defeitos
    result = geralCards_Email.groupby(['NR_OS', 'ATIVO_TL'], as_index=False).agg({
        'TREM': 'first',  # Manter o primeiro valor
        'Qtd_vg_Por_OS': 'first',
        'DataHoraPassagem' : 'first',
        'NOTA': 'first',  # Manter o primeiro valor
        'Pode_ir_para_TOM': 'first',
        'Obrigatoria': 'first',
        'Local': 'first',
        'Isolado': 'first',
        'Rec_Sistema': 'first',
        'Sequencia': 'first',
        'DT_NOTA': 'first',
        # Concatenar os valores de 'Defeitos'
        'Defeitos': lambda x: ' + '.join(x.astype(str)),
        'Observacao_Retencao':'first',
        'data_now': 'first'  # Manter o primeiro valor
    })
    # Depurar o número de resultados
    print(len(result))
    result['Categoria'] = result['NR_OS'].ne(result['NR_OS'].shift()).cumsum().apply(lambda x: 'A' if x % 2 == 0 else 'B')
    result = result.fillna("")
    
    result

    # Renderizar o template HTML com o DataFrame filtrado
    return render_template('email.html', df=result)


@app.route('/sucesso')
def sucesso():
    print("sucesso")
    tempoary_df = pd.read_csv('files//tempoary_df.csv')
    print(len(tempoary_df))
    return render_template('cards.html', df=tempoary_df)


@app.route('/cardsGeral')
def cardsGeral():
    print("cardsGeral")
    geralCards = pd.read_csv('files//submitted_data.csv')
    geralCards = geralCards.fillna(' ')
    geralCards = geralCards.replace('NaN', ' ')


    # Garantir que a coluna 'data_now' esteja no formato datetime
    # geralCards['data_now'] = pd.to_datetime(geralCards['data_now'])
    geralCards['data_now'] = pd.to_datetime(
        geralCards['data_now'], format="%d/%m/%Y %H:%M:%S")

    # Organizar o DataFrame pela coluna 'data_now'

    # Transformar 'data_now' de volta para string no formato desejado (exemplo: '%Y-%m-%d')
    geralCards['data_now'] = geralCards['data_now'].dt.strftime('%Y-%m-%d')
    geralCards = geralCards.sort_values(by='data_now', ascending=False)

    print(len(geralCards))
    return render_template('cards_Geral.html', df=geralCards)


@app.route('/upload', methods=['POST'])
def upload_file():
    global user_info
    if 'file' not in request.files:
        # user_info = "Sem dados Locais - APENAS STAGE"
        return redirect(url_for('lista'))

    file = request.files['file']

    if file.filename == '':
        # user_info = "Sem dados Locais - APENAS STAGE"
        return redirect(url_for('lista'))

    # Extrair a extensão do arquivo
    original_filename = file.filename
    file_extension = os.path.splitext(original_filename)[1]

    # Gerar um novo nome (exemplo: UUID ou nome fixo)
    new_filename = f"nota_export{file_extension}"

    # Caminho completo do arquivo salvo
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)

    # Salvar o arquivo
    file.save(filepath)
    data_atual = datetime.now()
    data_atual = data_atual.strftime("%d/%m/%Y %H:%M:%S")
    print("Data e hora atual:", data_atual)
    # user_info = "Dados Locais " + data_atual

    return redirect(url_for('lista'))


@app.route('/')  # pagina inicial
def index():

    df_log_hoje_old = pd.read_json(
        '\\\\fs-vwps02.all-logistica.net\\GRUPOS2\\CIM\\Coordenação de monitoramento de Material Rodante\\Data_STAGE\\df_log.json', orient='records', lines=True)
    df_log_hoje_old = df_log_hoje_old.tail(2)
    print(len(df_log_hoje_old))
    return render_template('index.html', df=df_log_hoje_old)


@app.route('/avd')  # pagina inicial
def avd():

    df_log_hoje_old = pd.read_json(
        '\\\\fs-vwps02.all-logistica.net\\GRUPOS2\\CIM\\Coordenação de monitoramento de Material Rodante\\Data_STAGE\\df_log.json', orient='records', lines=True)
    df_log_hoje_old = df_log_hoje_old.tail(20)
    return render_template('index.html', df=df_log_hoje_old)


@app.route('/card')  # pagina inicial
def card():
    return render_template('cards.html', df=df_stage_merge)


@app.route('/lista')  # pagina inicial
def lista():
    try:
        print("leitura df_QUERY_z369")
        df_QUERY_z369 = pd.read_json(r'files\df_stage_Nota.json', lines=True)
        df_QUERY_z369['Aux_Status'] = df_QUERY_z369['Aux_Status'].replace('Pendente', 'MSPN')
        df_QUERY_z369['Aux_Status'] = df_QUERY_z369['Aux_Status'].replace('Em processamento', 'MSPR')

# --------------------------------
        try:
            # Lista de novos cabeçalhos
            colunas = [
                "Data da nota", "Hora da nota", "Equipam.", "Parada", "Notificador", "TpNota",
                "CódFalha", "Descrição", "Texto do item", "Texto da causa", "Status do sistema",
                "Nota", "Centro trab.respons.", "Ordem"
            ]

            # Carregar o arquivo
            arquivo = r'uploads//nota_export.xlsx'
            df_QUERY_notasExport = pd.read_excel(arquivo, header=0)

            # Verifique se alguma coluna contém "Unnamed"
            if any("Unnamed" in col for col in df_QUERY_notasExport.columns):
                # Substitua pelos novos cabeçalhos
                df_QUERY_notasExport.columns = colunas
                print(
                    "Alguma coluna continha 'Unnamed'. Cabeçalhos substituídos com sucesso!")

            else:
                print("Nenhuma coluna contém 'Unnamed'. Mantendo o DataFrame original.")

        except Exception as e:
            # Captura qualquer erro e retorna uma mensagem personalizada
            error_message = f" PARA CORRIGIR SALVE O ARQUIVO ANEXADO NOVAMENTE, COM 'SALVAR COMO' NO SEU COMPUTADOR e ANEXE NOVAMENTE.Ocorreu um erro ao processar o arquivo: {str(e)}."
            print(error_message)
            return jsonify(message=error_message), 500
# --------------------------------
        print("leitura df_QUERY_TELA_164_FOTO")
        df_QUERY_TELA_164_FOTO = pd.read_json(
            r'files\df_QUERY_TELA_164_FOTO.json', lines=True)

        if not df_QUERY_notasExport.empty:
            print("nota_export OK")
            print(df_QUERY_notasExport)
            colunas_atuais = df_QUERY_notasExport.columns
            df_QUERY_notasExport_filtred = df_QUERY_notasExport[(df_QUERY_notasExport['Status do sistema'] == 'MSPN') |
                                                                (df_QUERY_notasExport['Status do sistema'] == 'MSPR')]

            mapa_colunas = {
                'Data da nota': 'DT_NOTA',
                'Hora da nota': 'Hora da nota',
                'Equipam.': 'ATIVO_TL',
                'Parada': 'Flag',
                'Notificador': 'Notificador',
                'TpNota': 'TP_NOTA',
                'CódFalha': 'CodFalha',
                'Descrição': 'TEXTO',
                'Texto do item': 'Texto_Item',
                'Texto da causa': 'Texto_Causa',
                'Status do sistema': 'Aux_Status',
                'Nota': 'NOTA',
                'Novo Descrição': 'TEXTO',
                'Novo Texto do item': 'Texto_Item',
                'Novo Texto da causa': 'Texto_Causa',
                'Modelo': 'ATIVO_TL'
            }

            colunas_convertidas = [mapa_colunas.get(
                col, col) for col in colunas_atuais]

            if len(colunas_convertidas) == len(colunas_atuais):
                df_QUERY_notasExport_filtred.columns = colunas_convertidas
            else:
                print(
                    "Erro: O número de colunas mapeadas não corresponde ao número de colunas no DataFrame.")

            df_QUERY_notasExport_filtred['BASE'] = "SAP_Arquivo_LOCAL"
            df_QUERY_z369['BASE'] = "SAP_STAGE"

            df_concatenado = pd.concat(
                [df_QUERY_z369, df_QUERY_notasExport_filtred])
            df_resultado_Export_z369_final = df_concatenado.drop_duplicates(
                subset=['NOTA'], keep='last')
            df_QUERY_z369 = df_resultado_Export_z369_final
        else:
            user_info = "Sem dados Locais - APENAS STAGE"
            print("nota_export NOK")

        if len(df_QUERY_TELA_164_FOTO) > 1000:
            print("df_QUERY_TELA_164_FOTO OK")
        else:
            print("df_QUERY_TELA_164_FOTO NOK")

        if len(df_QUERY_z369) > 1000:
            print("df_QUERY_z369 OK")
        else:
            print("df_QUERY_z369 NOK")
# ---------------------------------------------
        # Cria a coluna 'ATIVO_TL' na tabela df_QUERY_TELA_164_FOTO
        df_QUERY_TELA_164_FOTO['ATIVO_TL'] = df_QUERY_TELA_164_FOTO['VAGAO'].astype(
            str).str.zfill(7) + df_QUERY_TELA_164_FOTO['SERIE']

        # Garante que 'ATIVO_TL' em df_QUERY_z369 também seja do tipo string
        df_QUERY_z369['ATIVO_TL'] = df_QUERY_z369['ATIVO_TL'].astype(str)

        # Realiza a junção com how='left' para manter todos os registros de df_QUERY_TELA_164_FOTO
        df_stage_merge = pd.merge(
            df_QUERY_TELA_164_FOTO, df_QUERY_z369, on='ATIVO_TL', how='left')

        # Converte a coluna 'NR_OS' para string ou vazio, conforme necessário
        df_stage_merge['NR_OS'] = df_stage_merge['NR_OS'].apply(
            lambda x: str(int(x)) if pd.notnull(x) else '')
        df_stage_merge['key'] = df_stage_merge['NOTA'].astype(str) + \
            df_stage_merge['ATIVO_TL']

        # Remove as duplicatas baseadas na coluna 'NOTA', mantendo o primeiro registro
        df_stage_merge = df_stage_merge.drop_duplicates(
            subset='key', keep='first')

        # Converte 'DT_NOTA' para o formato desejado, lidando com erros
        df_stage_merge['DT_NOTA'] = pd.to_datetime(
            df_stage_merge['DT_NOTA'], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')

        # Garante que 'ATIVO_TL' sem notas também apareçam
        # Substitui valores NaN em colunas críticas para evitar inconsistências
        df_stage_merge = df_stage_merge.fillna({
            'NR_OS': '',
            'NOTA': '',
            'DT_NOTA': '',
            'Aux_Status': ''
        })



# ---------------------------------------------

        Pontuacao_trem = pd.pivot_table(
            df_stage_merge, index='NR_OS', columns='TP_NOTA', aggfunc='size', fill_value=0)
        Pontuacao_trem = Pontuacao_trem.reset_index()

        nr_os_unicos = df_stage_merge['NR_OS'].unique()
        Pontuacao_trem = Pontuacao_trem.set_index('NR_OS').reindex(
            nr_os_unicos, fill_value=0).reset_index()

        Pontuacao_trem = Pontuacao_trem.merge(
            df_stage_merge[['TREM', 'NR_OS']].drop_duplicates(), on='NR_OS', how='left')
        Pontuacao_trem = Pontuacao_trem.sort_values(
            by='M2', ascending=False).drop_duplicates().reset_index(drop=True)

        Pontuacao_trem = Pontuacao_trem[['TREM', 'M1', 'M2','M9','M6' , 'NR_OS']]
        Pontuacao_trem['TREM'] = Pontuacao_trem['TREM'].astype(str)
        Pontuacao_trem = Pontuacao_trem[(Pontuacao_trem['TREM'] != "None")]

        df = Pontuacao_trem

        print(df)
    except Exception as e:
        print(f"Erro: {e}")

    df_stage_merge = df_stage_merge.drop_duplicates(
        subset='key', keep='first')
    
# -------------- new
    # Contar a quantidade de ocorrências de cada chave em df2
    df_QUERY_TELA_164_FOTO['NR_OS'] = df_QUERY_TELA_164_FOTO['NR_OS'].fillna(
        0).astype(int).astype(str)
    # df_stage_merge['Qtd_vg_Por_OS'] = df_stage_merge['NR_OS']
    contagem = df_QUERY_TELA_164_FOTO.groupby('NR_OS')['VAGAO'].nunique()
    print(contagem)

    # Adicionar uma coluna ao df1 com base na contagem, garantindo que valores NA sejam tratados
    df_stage_merge['Qtd_vg_Por_OS'] = df_stage_merge['NR_OS'].map(
        contagem).fillna(0)

    # Certifique-se de que os valores NA sejam preenchidos corretamente antes de converter para int
    df_stage_merge['Qtd_vg_Por_OS'] = df_stage_merge['Qtd_vg_Por_OS'].astype(
        int)

    df_stage_merge = df_stage_merge.drop_duplicates(
        subset='key', keep='first')
# -------------- new


    df_stage_merge.to_json(
        'files\\df_stage_merge_saved.json', orient='records', lines=True)

    # Apenas para teste, exportar CSVa
    # df_stage_merge.to_csv('files//df_stage_merge.csv', index=False)
    return render_template('lista.html', df=df)


@ app.route('/save_id', methods=['GET'])
def save_id():
    # Obtém o valor do ID da query string
    # df_stage_merge = pd.read_csv('files//df_stage_merge.csv')
    # valor_filtro = request.args.get('id')
    df_stage_merge = pd.read_json(
        'files\\df_stage_merge_saved.json', orient='records', lines=True)

    valor_filtro = request.args.get('id')

    if not valor_filtro:
        return "Erro: Nenhum valor de filtro foi fornecido!", 400

    df_stage_merge = pd.read_json(
        'files\\df_stage_merge_saved.json', orient='records', lines=True)

    # Filtra o DataFrame com base no valor fornecido
    df_filtrado = df_stage_merge[df_stage_merge['NR_OS'] == valor_filtro]
    print(len(df_filtrado))
    print(df_filtrado.columns)
    print(df_filtrado.head())

    if df_filtrado.empty:
        return f"Nenhum resultado encontrado para o valor {valor_filtro}", 404

    # Processa os dados filtrados (pivot table)
    df_filtrado['TP_NOTA'] = df_filtrado['TP_NOTA'].fillna("Sem nota")
    print("A")

    b_resumo = pd.pivot_table(
        df_filtrado, index='ATIVO_TL', columns='TP_NOTA', aggfunc='size', fill_value=0)
    print("b")
    print(b_resumo.columns)
    b_resumo = b_resumo.reset_index()
    print("c")
    b_resumo = b_resumo.merge(
        df_filtrado[['ATIVO_TL', 'SEQUENCIA']], on='ATIVO_TL', how='left')
    print("d")
    b_resumo = b_resumo.sort_values(
        by='SEQUENCIA').drop_duplicates().reset_index()
    print("e")
    print(len(df_filtrado[df_filtrado['TP_NOTA'] == 'M2']))

    if len(df_filtrado[df_filtrado['TP_NOTA'] == "M2"]) == 0:
        print("entrou")
        b_resumo["M2"] = 0
    if len(df_filtrado[df_filtrado['TP_NOTA'] == "M1"]) == 0:
        print("entrou")
        b_resumo["M1"] = 0
    if len(df_filtrado[df_filtrado['TP_NOTA'] == "M6"]) == 0:
        print("entrou")
        b_resumo["M6"] = 0
    if len(df_filtrado[df_filtrado['TP_NOTA'] == "M9"]) == 0:
        print("entrou")
        b_resumo["M9"] = 0

    b_resumo = b_resumo[['ATIVO_TL', 'M1', 'M2', 'M6','M9','SEQUENCIA']]
    b_resumo['SEQUENCIA'] = b_resumo['SEQUENCIA'].astype(int).astype(str)

    # Renderiza a tabela filtrada em um template
    return render_template('filtered.html', df=b_resumo)


@ app.route('/notas', methods=['GET'])
def notas():
    # df_stage_merge = pd.read_csv('files//df_stage_merge.csv')

    df_stage_merge = pd.read_json(
        'files\\df_stage_merge_saved.json', orient='records', lines=True)
    # Obtém o valor do ID da query string
    valor_filtro = request.args.get('id')

    if not valor_filtro:
        return "Erro: Nenhum valor de filtro foi fornecido!", 400

    # Filtra o DataFrame com base no valor fornecido
    df_filtrado = df_stage_merge[df_stage_merge['NR_OS'] == valor_filtro]
    df_filtrado = df_filtrado.sort_values(by='SEQUENCIA')
    df_filtrado['TP_NOTA'] = df_filtrado['TP_NOTA'].fillna("Sem Nota")
    df_filtrado = df_filtrado.fillna("")
    colunas_desejadas = [
        "VAGAO", "ID_VAGAO", "SERIE", "TREM", "SEQUENCIA", "LOCAL",
        "ORIGEM", "DESTINO", "NR_OS", "COD_LINHA", "ATIVO_TL", "NOTA",
        "DT_NOTA", "Notificador", "Texto_Causa", "TP_NOTA", "TEXTO",
        "Texto_Item", "Texto_AVARIA", "DATA_QMDAT", "CodFalha", "Flag", "Aux_Status", "BASE","DESC_LOTACAO", "Qtd_vg_Por_OS"
    ]

    df_filtrado = df_filtrado[colunas_desejadas]
    # df_filtrado['SEQUENCIA'] = df_filtrado['SEQUENCIA'].astype(int).astype(str)
    # df_filtrado['NOTA'] = df_filtrado['NOTA'].astype(int).astype(str)
    notas_verificar = {'M2', 'M9', 'M6'}
    df_filtrado['nt_critica'] = df_filtrado.groupby('VAGAO')['TP_NOTA'].transform(lambda x: bool(set(x) & notas_verificar))
    print(len(df_filtrado))
    print(df_filtrado.columns)

    if df_filtrado.empty:
        return f"Nenhum resultado encontrado para o valor {valor_filtro}", 404

    # Renderiza o template 'notas.html' com os dados filtrados
    return render_template('notas.html', df=df_filtrado)


@ app.route('/atualizar', methods=['GET'])
def atualizar():
    def run_script():
        # Caminho do script Python a ser executado
        script_path = "C:\\src_Rumo\\script\\exerumo\\Scripts_On\\STAGE_toJSON_z364_FOTO_t164.py"

        # Executa o script e redireciona a saída para um processo
        process = subprocess.Popen(
            ["python", script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Envia a saída do script para o cliente em tempo real
        for line in process.stdout:
            yield f"data: {line}\n\n"
            time.sleep(1)  # Delay para simular o progresso

        # Captura erros do processo e envia para o cliente
        for line in process.stderr:
            yield f"data: {line}\n\n"
            time.sleep(1)

    return Response(run_script(), content_type='text/event-stream')


# Executa a aplicação
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
