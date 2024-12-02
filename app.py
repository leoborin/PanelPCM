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
            "DESTINO", "NR_OS", "ATIVO_TL", "NOTA", "DT_NOTA", "Notificador",
            "Texto_Causa", "TP_NOTA", "TEXTO", "Texto_Item", "Texto_AVARIA",
            "DATA_QMDAT", "CodFalha", "Flag", "Aux_Status", "BASE"
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
            'NOTA': item.get('NOTA'),
            'Pode_ir_para_TOM': item.get('Pode_ir_para_TOM'),
            'Obrigatoria': item.get('Obrigatoria'),
            'Isolado': item.get('Isolado'),
            'Rec_Sistema': item.get('Rec_Sistema'),
            'Sequencia': item.get('Sequencia'),
            'DT_NOTA': item.get('DT_NOTA'),
            'TEXTO': item.get('TEXTO'),
            'Texto_Causa': item.get('Texto_Causa'),
            'TP_NOTA': item.get('TP_NOTA')
        })

    # Criar um DataFrame com os dados processados
    df_submitted = pd.DataFrame(processed_data)
    df_submitted_OLD = pd.read_csv('files//submitted_data.csv')
    data_atual = datetime.now()
    data_atual = data_atual.strftime("%d/%m/%Y %H:%M:%S")

    df_submitted['data_now'] = data_atual
    result = pd.concat([df_submitted, df_submitted_OLD])
    result = result.drop_duplicates(subset=['NOTA'])

    # Exemplo de salvar em CSV (pode ser ajustado para banco de dados ou outro método)
    result.to_csv('files//submitted_data.csv', index=False)

    return redirect(url_for('cardsGeral'))


@app.route('/email')
def email():
    print("email")
    # Carregar o arquivo CSV
    geralCards = pd.read_csv('files//submitted_data.csv')

    # Filtrar apenas as linhas com TP_NOTA == 'M2'
    geralCards_Email = geralCards[geralCards['TP_NOTA'] == 'M2']

    # Obter o parâmetro `id` da URL e converter para uma lista
    OSfilters = request.args.get('id')  # Exemplo: "1989210,1989564"
    if OSfilters:
        OSfilters = OSfilters.split(',')  # ["1989210", "1989564"]
        OSfilters = [int(id.strip())
                     for id in OSfilters]  # Convertendo para inteiros

    # Filtrando o DataFrame com os IDs fornecidos
    geralCards_Email = geralCards_Email[geralCards_Email['NR_OS'].isin(
        OSfilters)]

    geralCards_Email['Defeitos'] = geralCards_Email['TEXTO'].astype(str) + \
        " " + geralCards_Email['Texto_Causa'].astype(str)

    # Agrupar por 'NR_OS' e concatenar os defeitos
    result = geralCards_Email.groupby(['NR_OS', 'ATIVO_TL'], as_index=False).agg({
        'TREM': 'first',  # Manter o primeiro valor
        'NOTA': 'first',  # Manter o primeiro valor
        'Pode_ir_para_TOM': 'first',
        'Obrigatoria': 'first',
        'Isolado': 'first',
        'Rec_Sistema': 'first',
        'Sequencia': 'first',
        'DT_NOTA': 'first',
        # Concatenar os valores de 'Defeitos'
        'Defeitos': lambda x: ' + '.join(x.astype(str)),
        'data_now': 'first'  # Manter o primeiro valor
    })
    # Depurar o número de resultados
    print(len(result))

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

    # Garantir que a coluna 'data_now' esteja no formato datetime
    geralCards['data_now'] = pd.to_datetime(geralCards['data_now'])

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
        user_info = "Sem dados Locais - APENAS STAGE"
        return redirect(url_for('lista'))

    file = request.files['file']

    if file.filename == '':
        user_info = "Sem dados Locais - APENAS STAGE"
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
    user_info = "Dados Locais " + data_atual

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
    print("leituradf_QUERY_z369")
    df_QUERY_z369 = pd.read_json(
        'files\df_stage_Nota.json', lines=True)
    print("leituradf_notasExport")
    df_QUERY_notasExport = pd.read_excel(
        'uploads//nota_export.xlsx')
    print("leituradf_QUERY_TELA_164_FOTO")
    df_QUERY_TELA_164_FOTO = pd.read_json(
        'files\df_QUERY_TELA_164_FOTO.json', lines=True)

    # df_QUERY_TELA_164_FOTO_teste = df_QUERY_TELA_164_FOTO[(df_QUERY_TELA_164_FOTO['TREM'] == 'C65')]
    # print("C65")
    # print(len(df_QUERY_TELA_164_FOTO_teste))

    if len(df_QUERY_notasExport) > 1:
        print("nota_export OK ")
        # Obter os nomes atuais das colunas
        colunas_atuais = df_QUERY_notasExport.columns
        df_QUERY_notasExport_filtred = df_QUERY_notasExport[(df_QUERY_notasExport['Status do sistema'] == 'MSPN') | (
            df_QUERY_notasExport['Status do sistema'] == 'MSPR')]

        # Mapeamento entre nomes antigos e novos
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

        # Criar uma lista de novos nomes, mantendo os originais onde não há correspondência
        colunas_convertidas = [mapa_colunas.get(
            col, col) for col in colunas_atuais]

        # Garantir que o número de nomes no mapeamento corresponda ao número de colunas
        if len(colunas_convertidas) == len(colunas_atuais):
            # Renomear as colunas no DataFrame `df_QUERY_notasExport`
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

    else:
        user_info = "Sem dados Locais - APENAS STAGE"
        print("nota_export NOK")

    if len(df_QUERY_TELA_164_FOTO) > 1000:
        print("df_QUERY_TELA_164_FOTO OK ")
    else:
        print("df_QUERY_TELA_164_FOTO NOK ")

    if len(df_QUERY_z369) > 1000:
        print("df_QUERY_z369 OK ")
    else:
        print("df_QUERY_z369 NOK ")

    # ponto chave para textes
    df_QUERY_z369 = df_resultado_Export_z369_final
    df_QUERY_z369_bkp = df_resultado_Export_z369_final

    # ponto chave para textes

    df_QUERY_TELA_164_FOTO["ATIVO_TL"] = df_QUERY_TELA_164_FOTO["VAGAO"].astype(
        str) + df_QUERY_TELA_164_FOTO["SERIE"].astype(str)
    df_QUERY_TELA_164_FOTO['ATIVO_TL'] = df_QUERY_TELA_164_FOTO['VAGAO'].astype(
        str).str.zfill(7) + df_QUERY_TELA_164_FOTO['SERIE']
    df_stage_merge = pd.merge(df_QUERY_TELA_164_FOTO,
                              df_QUERY_z369, on='ATIVO_TL', how='left')  # ERRO aqui !!

    # df_stage_merge_teste = df_stage_merge[(df_stage_merge['TREM'] == 'C65')]
    # print("C65 - 2")
    # print(len(df_stage_merge_teste))

    df_stage_merge['NR_OS'] = df_stage_merge['NR_OS'].apply(
        lambda x: str(int(x)) if pd.notnull(x) else '')
    df_stage_merge = df_stage_merge[(
        df_stage_merge['Aux_Status'] != "Em processamento")]

    # Reiniciar opções de exibição do pandas
    pd.reset_option('display.max_rows')
    pd.reset_option('display.max_columns')
    pd.reset_option('display.width')
    pd.reset_option('display.max_colwidth')

    # Criar a pivot table, preenchendo valores ausentes com 0
    Pontuacao_trem = pd.pivot_table(
        df_stage_merge, index='NR_OS', columns='TP_NOTA', aggfunc='size', fill_value=0)

    # Resetar o índice para facilitar o acesso às colunas
    Pontuacao_trem = Pontuacao_trem.reset_index()

    # Garantir que todos os NR_OS possíveis estejam no dataframe
    # Adicionar NR_OS ausentes, preenchendo com zeros
    nr_os_unicos = df_stage_merge['NR_OS'].unique()
    Pontuacao_trem = Pontuacao_trem.set_index('NR_OS').reindex(
        nr_os_unicos, fill_value=0).reset_index()

    # Exibir para testes
    print(Pontuacao_trem)

    # Teste específico com NR_OS 1989764
    # Pontuacao_trem_teste = Pontuacao_trem[(Pontuacao_trem['NR_OS'] == 1989764)]
    # print("C65 - 3")
    # print(len(Pontuacao_trem_teste))

    # Mesclar com as informações de TREM e NR_OS
    Pontuacao_trem = Pontuacao_trem.merge(
        df_stage_merge[['TREM', 'NR_OS']].drop_duplicates(), on='NR_OS', how='left'
    )

    # Ordenar, remover duplicatas e selecionar colunas relevantes
    Pontuacao_trem = Pontuacao_trem.sort_values(
        by='M2', ascending=False).drop_duplicates().reset_index(drop=True)

    Pontuacao_trem = Pontuacao_trem[['TREM', 'M1', 'M2', 'NR_OS']]

    # Converter a coluna TREM para string e filtrar valores não desejados
    Pontuacao_trem['TREM'] = Pontuacao_trem['TREM'].astype(str)
    Pontuacao_trem = Pontuacao_trem[(Pontuacao_trem['TREM'] != "None")]

    # Preparar o dataframe final para renderizar
    df = Pontuacao_trem

    # Mesclar dados adicionais para DF_STAGE_MERGE
    df_QUERY_TELA_164_FOTO["ATIVO_TL"] = df_QUERY_TELA_164_FOTO["VAGAO"].astype(
        str) + df_QUERY_TELA_164_FOTO["SERIE"].astype(str)
    df_stage_merge = pd.merge(df_QUERY_TELA_164_FOTO,
                              df_QUERY_z369, on='ATIVO_TL', how='left')
    df_stage_merge['NR_OS'] = df_stage_merge['NR_OS'].apply(
        lambda x: str(int(x)) if pd.notnull(x) else ''
    )
    df_stage_merge['DT_NOTA'] = pd.to_datetime(
        df_stage_merge['DT_NOTA'], dayfirst=True, errors='coerce'
    ).dt.strftime('%Y-%m-%d')

    # Apenas para teste, exportar CSV
    # df_stage_merge.to_csv('files//df_stage_merge.csv', index=False)
    return render_template('lista.html', df=df, user_info=user_info)


@app.route('/save_id', methods=['GET'])
def save_id():
    # Obtém o valor do ID da query string
    # df_stage_merge = pd.read_csv('files//df_stage_merge.csv')
    valor_filtro = request.args.get('id')

    if not valor_filtro:
        return "Erro: Nenhum valor de filtro foi fornecido!", 400

    # Filtra o DataFrame com base no valor fornecido
    df_filtrado = df_stage_merge[df_stage_merge['NR_OS'] == valor_filtro]
    print(len(df_filtrado))
    print(df_filtrado.columns)

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

    b_resumo = b_resumo[['ATIVO_TL', 'M1', 'M2', 'SEQUENCIA']]
    b_resumo['SEQUENCIA'] = b_resumo['SEQUENCIA'].astype(int).astype(str)

    # Renderiza a tabela filtrada em um template
    return render_template('filtered.html', df=b_resumo)


@app.route('/notas', methods=['GET'])
def notas():
    # df_stage_merge = pd.read_csv('files//df_stage_merge.csv')
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
        "Texto_Item", "Texto_AVARIA", "DATA_QMDAT", "CodFalha", "Flag", "Aux_Status", "BASE"
    ]
    df_filtrado = df_filtrado[colunas_desejadas]
    # df_filtrado['SEQUENCIA'] = df_filtrado['SEQUENCIA'].astype(int).astype(str)
    # df_filtrado['NOTA'] = df_filtrado['NOTA'].astype(int).astype(str)

    print(len(df_filtrado))
    print(df_filtrado.columns)

    if df_filtrado.empty:
        return f"Nenhum resultado encontrado para o valor {valor_filtro}", 404

    # Renderiza o template 'notas.html' com os dados filtrados
    return render_template('notas.html', df=df_filtrado)


@app.route('/atualizar', methods=['GET'])
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
