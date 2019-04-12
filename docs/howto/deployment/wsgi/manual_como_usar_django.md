============================
Como usar o Django com o uWSGI
============================

.. destaque :: bash

O uWSGI_ é um aplicativo rápido, auto-reparável e amigável ao desenvolvedor / sysadmin
servidor de contêiner codificado em C. puro

.. _uWSGI: https://uwsgi-docs.readthedocs.io/

.. Veja também::

    Os documentos do uWSGI oferecem um 'tutorial`_ cobrindo Django, nginx e uWSGI (um
    configuração de implantação possível de muitos). Os documentos abaixo estão focados em como
    integre o Django com o uWSGI.

    .. _tutorial: https://uwsgi.readthedocs.io/en/latest/tutorials/Django_and_nginx.html

Pré-requisito: uWSGI
===================

O wiki do uWSGI descreve vários `procedimentos de instalação`_. Usando pip, o
Gerenciador de pacotes Python, você pode instalar qualquer versão do uWSGI
comando. Por exemplo:

.. code-block :: console

    # Instale a versão estável atual.
    $ pip instalar o uwsgi

    # Ou instale o LTS (suporte a longo prazo).
    $ pip install https://projects.unbit.it/downloads/uwsgi-lts.tar.gz

.. _procedimentos de instalação: https://uwsgi-docs.readthedocs.io/en/latest/Install.html

modelo uWSGI
-----------

O uWSGI opera em um modelo cliente-servidor. Seu servidor da Web (por exemplo, nginx, Apache)
comunica com um processo `django-uwsgi`" worker "para servir conteúdo dinâmico.

Configurando e iniciando o servidor uWSGI para Django
-------------------------------------------------- -

O uWSGI suporta várias formas de configurar o processo. Veja o uWSGI's
`documentação de configuração`_.

.. documentação _configuration: https://uwsgi.readthedocs.io/en/latest/Configuration.html

Aqui está um exemplo de comando para iniciar um servidor uWSGI ::

    uwsgi --chdir = / caminho / para / seu / projeto \
        --module = mysite.wsgi: aplicação \
        --env DJANGO_SETTINGS_MODULE = mysite.settings \
        --master --pidfile = / tmp / projectmaster.pid \
        --socket = 127.0.0.1: 49152 \ # também pode ser um arquivo
        --processos = 5 \ # número de processos de trabalho
        --uid = 1000 --gid = 2000 \ # se root, o uwsgi pode descartar privilégios
        --harakiri = 20 \ # processos respawn demorando mais de 20 segundos
        --max-requests = 5000 \ # processos respawn após atender a 5000 solicitações
        - vácuo ambiente limpo ao sair
        --home = / caminho / para / virtual / env \ # caminho opcional para um virtualenv
        --daemonize = / var / log / uwsgi / yourproject.log # background o processo

Isso pressupõe que você tenha um pacote de projeto de nível superior chamado `` mysite`` e
dentro dele um módulo: file: `mysite / wsgi.py` que contém um` `application`` do WSGI
objeto. Este é o layout que você terá se executar o `` django-admin
startproject mysite`` (usando seu próprio nome de projeto no lugar de `` mysite``) com
uma versão recente do Django. Se este arquivo não existir, você precisará criar
isto. Veja a documentação: doc: `/ howto / deployment / wsgi / index` para o padrão
conteúdo que você deve colocar neste arquivo e o que mais você pode adicionar a ele.

As opções específicas do Django são:

* `` chdir``: O caminho para o diretório que precisa estar na importação do Python
  caminho - isto é, o diretório contendo o pacote `` mysite``.
* `` module``: O módulo WSGI para usar - provavelmente o módulo `` mysite.wsgi``
  que: djadmin: `startproject` cria.
* `` env``: provavelmente deve conter pelo menos `` DJANGO_SETTINGS_MODULE``.
* `` home``: Caminho opcional para o seu projeto virtualenv.

Exemplo de arquivo de configuração ini ::

    [uwsgi]
    chdir = / path / to / your / project
    module = mysite.wsgi: application
    mestre = verdadeiro
    pidfile = / tmp / project-master.pid
    vácuo = verdadeiro
    max-requests = 5000
    daemonize = / var / log / uwsgi / yourproject.log

Exemplo de uso do arquivo de configuração ini ::

    uwsgi --ini uwsgi.ini

.. admonition :: Corrigindo `` UnicodeEncodeError`` para uploads de arquivos

    Se você obtiver um `` UnicodeEncodeError`` ao carregar arquivos com nomes de arquivos
    que contêm caracteres não-ASCII, certifique-se de que o uWSGI esteja configurado para aceitar
    nomes de arquivos não-ASCII adicionando isto ao seu `` uwsgi.ini`` ::

        env = LANG = en_US.UTF-8

    Veja a seção: ref: `unicode-files` do guia de referência Unicode para
    detalhes.

Veja os documentos do uWSGI sobre `gerenciamento do processo uWSGI`_ para obter informações sobre
iniciar, parar e recarregar os trabalhadores do uWSGI.

.. _managing o processo uWSGI: https://uwsgi-docs.readthedocs.io/en/latest/Management.html
