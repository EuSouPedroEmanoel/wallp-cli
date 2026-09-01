# wallp

CLI para trocar o wallpaper (animado ou imagem) do **KDE Plasma** usando o plasmoid
**Smart Video Wallpaper Reborn**, com modo automático por agenda.

[![Release](https://img.shields.io/github/v/release/EuSouPedroEmanoel/wallp-cli?label=Download&sort=semver)](https://github.com/EuSouPedroEmanoel/wallp-cli/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![KDE Plasma 6](https://img.shields.io/badge/KDE-Plasma%206-1daee9?logo=kde)](https://kde.org/plasma-desktop/)

## 📥 Download / Instalação rápida

**Sem `git clone` — sempre na última release estável (tarball):**

| Método | Comando |
|---|---|
| **curl** (recomendado) | `curl -fsSL https://raw.githubusercontent.com/EuSouPedroEmanoel/wallp-cli/master/quick-install.sh \| bash` <br> `curl -fsSL .../quick-install.sh \| bash -s -- -y` (sem perguntar) |
| **ZIP / TAR.GZ** | [wallp-cli-1.0.2.zip](https://github.com/EuSouPedroEmanoel/wallp-cli/releases/latest/download/wallp-cli-1.0.2.zip) / [tar.gz](https://github.com/EuSouPedroEmanoel/wallp-cli/releases/latest/download/wallp-cli-1.0.2.tar.gz) → `unzip ... && cd wallp-cli-* && ./install.sh -y` |
| **git clone** | `git clone https://github.com/EuSouPedroEmanoel/wallp-cli.git ~/dev/wallp/wallp-cli && ~/dev/wallp/wallp-cli/install.sh -y` |

> `quick-install.sh` baixa o tarball da última release por padrão (sem `git`/`jq`). `install.sh` cuida de `python-dbus`, `python-yaml`, `qt6-multimedia-ffmpeg`, plasmoid e daemon.

Versões antigas: https://github.com/EuSouPedroEmanoel/wallp-cli/releases — ex. `1.0.0`: `curl .../quick-install.sh | bash -s -- --version 1.0.0` ou baixe [wallp-cli-1.0.0.zip](https://github.com/EuSouPedroEmanoel/wallp-cli/releases/download/v1.0.0/wallp-cli-1.0.0.zip) / `--version 1.0.0 --git` para clonar a tag.

## Requisitos

- KDE Plasma 6 (Wayland/X11) com `plasmashell` rodando
- Python 3 com `dbus-python` e `PyYAML`
- Plasmoid [Smart Video Wallpaper Reborn](https://github.com/luisbocanegra/plasma-smart-video-wallpaper-reborn) + `qt6-multimedia-ffmpeg` (codecs)
- systemd (sessão de usuário) para o daemon

## Instalação

```sh
./install.sh           # verifica e instala o que faltar (pede confirmação)
./install.sh -y        # instala tudo sem perguntar (usa sudo / yay)
./install.sh --check   # só verifica, não altera nada
```

O instalador garante:

- pacotes Arch (`python-dbus`, `python-yaml`, `qt6-multimedia`, `qt6-multimedia-ffmpeg`)
- o plasmoid Smart Video Wallpaper Reborn (via `yay` se faltar)
- o comando `wallp` em `~/.local/bin`
- o config `~/.config/wallp/wallp.yml` (se não existir)
- o daemon systemd `wallp-daemon.service`, habilitado para iniciar com o computador
- (opcional) um `.venv` para rodar os testes

## Comandos

```sh
wallp -c                       # próximo wallpaper do yml (caminho/nome)
wallp -n                       # próximo wallpaper do yml (igual -c sem nada)
wallp -c celeste               # por nome definido no yml
wallp -c ~/Vídeos/foo.mp4      # por caminho (vídeo ou imagem)
wallp -c ~/Vídeos/Wallpaper    # por pasta (aplica o primeiro arquivo)
wallp -c "Lista de exemplo"    # roda a lista do yml (uma passada; -l true = loop)
wallp -c "Lista de exemplo" -t 30m -q 10 -rep   # lista como slideshow (args do -r)
wallp -r -t 30m                # modo aleatório: pasta pessoal (~) inteira (subpastas)
wallp -r ~/Vídeos/Wallpaper -t 2h   # modo aleatório de uma pasta (recursivo)
wallp -r -q 10 -t 15m          # mostra 10 wallpapers e volta à agenda
wallp -r -m 6h -t 30m          # no máximo 6h e volta à agenda
wallp -r -l true -t 30m        # loop infinito (não aceita -m nem -q)
wallp -r -l 3 -t 30m           # 3 passadas na fila e volta à agenda
wallp -r -rep -t 30m           # vídeos repetem a reprodução (loop playback)
wallp -r -i -t 30m             # só imagens
wallp -r -v -s on -t 30m       # só vídeos, com som
wallp -r -s on                 # som ligado na fila mista
wallp -r -int -q 10            # vídeo toca inteiro e avança (imagem usa 30m)
wallp -r -v -int -t 1m -rep    # vídeo curto repete até completar 1m
wallp -n                       # próximo: da fila aleatória (se ativa) ou do yml
wallp -a                       # ativa o modo automático (agenda do yml)
wallp -a "Lista de exemplo"    # igual -c <nome> mas persistente até -x (loop do yml)
wallp -a celeste               # mantém só esse item do yml (diretório cicla se loop)
wallp -x                       # desativa o modo automático/aleatório e esvazia o buffer (500MB LRU)
wallp -x cache                 # limpa só o buffer do YouTube (tmpfs), sem parar o daemon
wallp -log [N]                 # logs em /tmp/wallp.log (apagado no boot)
                               # sozinho: mostra as últimas N linhas (padrão 50)
                               # com -a/-r/-c/-n/-x: roda o comando e segue o log (tail -f)
wallp -h                       # ajuda
wallp --init                   # cria um wallp.yml de exemplo
```

`-d` é interno (o daemon); o usuário não digita.

### Modo aleatório (`-r`)

- `wallp -r [dir] [-t tempo] [-m máx] [-q N] [-l true]` embaralha as mídias e mostra
  uma a cada `tempo` (padrão `30m`).
- Sem `dir`, varre a **pasta pessoal (`~`) inteira** — todas as subpastas (menos as
  ocultas, que começam com `.`) — pra pegar tudo.
- `dir` pode ser uma pasta (varredura recursiva) ou um arquivo (usa a pasta dele).
- `-m máx`: tempo máximo de duração (padrão **1h**) — quando bate, o slideshow termina.
- `-q N`: quantidade de wallpapers a mostrar — quando bate, o slideshow termina.
- `-l true`: **loop infinito** — só para com `-x`; **não aceita `-m` nem `-q`** (erro).
- `-l N`: roda a fila **N passadas** e volta à agenda (também não aceita `-m` nem `-q`).
- `-l` (sem valor) ou omitido = `false`; `-m` omitido = `1h`.
- `-rep`: vídeos da fila **repetem a reprodução** (loop de playback). Equivale a
  `repetir: true` de um item do yml. Só é válido com `-r` (erro caso contrário).
- `-i`: fila **só com imagens**; `-v`: fila **só com vídeos** (mutuamente exclusivos).
- `-int`: cada **vídeo toca inteiro** e o próximo entra quando ele termina (a duração é lida
  com `ffprobe`); em **imagem** vale o intervalo padrão (30m). Com `-t`, o vídeo que
  termina antes **fica no último frame** até o tempo acabar; com `-rep` (ou `repetir: true`
  do yml) ele **repete até completar o tempo**. `-q`/`-m`/`-l true` valem e descontam pela
  duração do vídeo (ou pelo `-t`, o que for maior). Equivale a `integro: true` do yml.
- `-s on`/`-s off`: som do vídeo (vale com qualquer `-r`). Padrão **off (mudo)**. Equivale
  a `som: true/false`.
- **Roda no daemon systemd**: o comando só grava a config e (re)inicia o serviço —
  **Ctrl+C não fecha**. Para parar: `wallp -x`.
- Ao **terminar** (bateu `-m`, `-q` ou acabou a lista sem loop), o daemon **volta para a
  agenda do yml** sozinho (como `-a`). `-a` também volta na hora.
- A ordem embaralhada é **estável o dia todo** (seed = data + salt) e muda à meia-noite.
- **Posição da fila** fica salva em `~/.local/state/wallp/pos` e é **compartilhada** entre
  o daemon e o `-n`: cada `-n` avança a fila, e o daemon continua de onde parou. `-n`
  também desconta 1 de `-q` e desconta o `tempo` de `-m`. A rotação não reinicia em `[1/N]`
  a cada restart do daemon.

## Configuração — `~/.config/wallp/wallp.yml`

```yaml
- nome: manha
  type: diretório              # opcional; local é uma pasta
  local: ~/Vídeos/Wallpaper
  tempo: 30m                   # em diretório = intervalo entre os arquivos
  loop: true                   # true=cicla; N=cicla N vezes; false=mostra 1x e sai
  hora: "9h-10h"               # range (opcional)

- nome: Lista de exemplo        # lista: um grupo nomeado de wallpapers
  list:
    - nome: manha
      type: diretório
      local: ~/Vídeos/Wallpaper
      tempo: 30m
      loop: true
      shuffled: true
      hora: "8h-11h"
    - nome: tarde
      type: diretório
      local: ~/Vídeos/Wallpaper
      tempo: 30m
      loop: true
      shuffled: true
      hora: "12h-18h"

- nome: tarde
  local: ~/Vídeos/Wallpaper/tarde.mp4
  tempo: 2h                    # arquivo: fica ativo por esse tempo

- nome: padrao
  local: ~/Vídeos/Wallpaper/padrao.mp4
  default: true                # o padrão, preenche os intervalos vazios
```

### Campos

| tag | descrição |
| --- | --- |
| `nome` | nome usado no `wallp -c <nome>` (fallback: nome do arquivo) |
| `local` | caminho do wallpaper — vídeo (`.mp4`, `.mkv`, `.webm`, …), imagem (`.png`, `.jpg`, …) ou pasta |
| `type: diretório` | `local` é uma pasta; `tempo` vira o intervalo entre os arquivos (ordem de nome) |
| `loop` | diretório/lista: `true` cicla infinito (até uma hora interromper); `N` cicla **N vezes** e volta à agenda; `false` mostra cada um 1x e sai. Em **vídeo/youtube**: `true` trava o playback em loop infinito (o vídeo fica até o fim do slot/dia) — e não pode ter `tempo` junto (erro) |
| `shuffled` | diretório em ordem **aleatória** (mesma o dia todo, muda à meia-noite) |
| `repetir` | o vídeo **repete a reprodução** (loop de playback) só até o `tempo` do item acabar (não ignora o tempo); aceita `repeat`. Para travar o vídeo infinitamente, use `loop: true` no vídeo (sem `tempo`) |
| `som` | vídeo **com som** (`true`) ou mudo (`false`, padrão); aceita `sound` |
| `integro` | o vídeo **toca inteiro**; com `tempo`, se terminar antes fica no último frame até o tempo acabar; `repetir: true` faz repetir até completar o tempo. Em diretório, `tempo` vira opcional e a troca é pelo fim do vídeo (aceita `integrado`/`integred`) |
| `hora` | `HH:MM`, `"9h"`, `"9h30m"`, ou range `"9h-10h"` |
| `tempo` | duração: `30m`, `2h`, `1d`, `1h30m10s` (também número puro = minutos) |
| `dia` | (opcional) só roda em dias específicos: `seg`/`ter`/`qua`/`qui`/`sex`/`sab`/`dom` (toda semana), `N` 1–31 (todo dia N do mês), `DD-MM` (todo ano, ex.: `01-04`), ou `DD-MM-AAAA` (só nesse dia, ex.: `20-12-2026`). Sem `dia`, vale todos os dias. No dia, quanto mais específico, primeiro: data > `DD-MM` > dia do mês > weekday > sem `dia` |
| `default: true` | o padrão; preenche os intervalos vazios (aceita `padrão: true`). O `-a` exige um **default global** (`default: true` sem `dia`), único; defaults com `dia` valem só no dia deles |
| `list` | lista de sub-itens (cada um um wallpaper completo). Com `hora`/`tempo` na lista, ela é um item da agenda que cicla os sub-itens; sem, os sub-itens entram direto na agenda (grupo nomeado). Aceita **listas dentro de listas**; sub sem `dia` herda o `dia` da lista |

### Listas (`list`)

- Cada sub-item é um wallpaper completo (`nome`/`local`/`type`/`tempo`/`hora`/`loop`/`shuffled`/…). Sub sem `tempo` herda o `tempo` da lista; sub sem `dia` herda o `dia` da lista (o `dia` próprio do sub vence).
- **Agrupamento** (lista sem `hora`/`tempo`): os sub-itens entram na agenda do dia como itens normais, cada um com sua `hora`/`tempo`. A lista é só o nome do grupo.
- **Unidade** (lista com `hora` e/ou `tempo`): ocupa um slot da agenda como item normal; dentro dela os sub-itens rodam em sequência pelo tempo de cada um.
- **Listas aninhadas**: um sub-item pode ter `list:` de novo (unidade vira sub-item; agrupamento achata os subs no nível acima). O `sub_nome` vira caminho (`pai/filho`).
- `wallp -c <nome-da-lista>`: roda **só a lista**. Sem args, uma passada e volta à agenda; `-l true` faz **loop até `-x`**; `-l N` faz **N passadas** e volta à agenda. Aceita os mesmos args do `-r` (`-t`, `-m`, `-q`, `-l`, `-rep`, `-i`, `-v`, `-int`, `-s`), virando um slideshow da lista.
- `wallp -a <nome-da-lista>`: igual `-c <nome>` mas **persistente até `-x`**, usando o campo **`loop` do yml** (`true` = infinito; `N` = N passadas e volta à agenda). `wallp -a <nome-de-item>` mantém só aquele item (diretório cicla se `loop: true`; vídeo com `loop: true` fica travado no playback). Ambos **exigem o default global** no yml.

### Regras

- **`dia`** restringe o item aos dias que casam (weekday, dia do mês, dia do ano
  `DD-MM` ou data `DD-MM-AAAA`). Fora do dia o item é **ignorado na agenda**: não entra
  na rotação, não ocupa slot de hora e não vira default. Item com `dia` no passado
  (data específica) nunca entra. Vale para itens, listas e sub-itens de listas.
- **Especificidade no dia**: sem hora, a rotação do dia mais **específico** roda primeiro
  (data > `DD-MM` > dia do mês > weekday > sem `dia`); se ela terminar **sem loop**, passa
  pro genérico seguinte e segue o caminho até o default. Se a rotação do dia estiver em
  **loop**, os genéricos não tocam naquele dia. O **default** usado é o mais específico ativo
  (default do dia vence o global); o **default global** (sem `dia`) é o último recurso.
- **`hora`** tem prioridade: quando chega o horário, substitui qualquer tempo/diretório.
  - range (`"9h-10h"`) → termina às 10h.
  - só início (`"9h"`) → **exige `tempo`** (fim = início + tempo). Range já define o fim.
- **tempo/diretório** (sem hora) formam uma sequência na ordem do dia (específico primeiro),
  preenchendo o tempo livre de forma **cumulativa** (recomeça às 00:00). Se uma hora
  interromper no meio do turno, ao terminar o turno **continua de onde parou**.
- **Fim da sequência**: com `default: true`, o padrão fica até a próxima hora (diretório-default
  cicla os arquivos). Sem default, a sequência **cicla de volta** ao primeiro.
- **`-a` exige um default global** (exatamente 1 `default: true` sem `dia`) no yml; sem ele
  (ou com mais de um), o `wallp -a` mostra o erro e sai com código 1. O `-c` não valida isso.

## Daemon

- unit `wallp-daemon.service` (`WantedBy=default.target`) — inicia com o computador.
- Ao subir, checa o estado em `~/.local/state/wallp/auto`: `off` → se fecha (exit 0).
  Se houver `~/.local/state/wallp/random` (JSON com `dir`/`tempo`/`max`/`qtd`/`loop`/`rep`/
  `tipo`/`integro`/`som`), roda o **modo aleatório** (`-r`). Se houver
  `~/.local/state/wallp/list` (JSON com `nome`/`loop`/args), roda o **modo lista**
  (`-c <lista>`/`-a <nome>`); senão, aplica a agenda do yml
  re-lendo a cada ciclo. `-m`/`-q`/`tempo` ficam em **segundos** no arquivo; `-m`/`-q` são
  compartilhados entre daemon e `-n` (cada um desconta). Ao bater o limite, o daemon limpa
  o random e **volta à agenda do yml**. Com `integro`, a troca usa a duração do vídeo
  (ffprobe) no lugar do timer.
- `wallp -r`/`wallp -a`/`wallp -c <lista>` gravam a config e (re)iniciam o serviço; `wallp -x` grava `off`,
  limpa a config random/lista e **para o daemon na hora** (a unit continua habilitada) e **esvazia o buffer do YouTube**.
- **Buffer do YouTube** (`-y`/`-yl`): fica em `tmpfs` em `/run/user/<uid>/wallp` (RAM, limpo no logout), com **limite de 500 MiB** (`YT_CACHE_MB`, override por env `WALLP_YT_CACHE_MB`). Após cada `download_yt()` bem-sucedido, limpeza **LRU por mtime**: mantém o arquivo recém-baixado (`keep`) e os mais recentes que caibam no orçamento; apaga o resto. Falha de download não limpa. `wallp -x cache` limpa só o buffer (sem tocar no daemon/estado); `wallp -x <outra-coisa>` erro.
- O daemon roda destacado do terminal — **Ctrl+C não o fecha**; pare com `wallp -x`.

## Pendente conhecido: `-n` depois de `-a`

Bug relatado: após `wallp -a` (agenda), `wallp -n` não avança para o próximo wallpaper
da fila nem pula de forma útil o wallpaper de horário — costuma cair no item de
rotação/default em vez do próximo slot.

Causa raiz (diagnóstico, sem correção ainda):

1. O daemon nunca grava `state.set_last`: `_run_schedule` (`daemon.py:395`) mantém a
   posição só em memória (`last_applied`). Em `-n`, `_change_yml_next`
   (`__init__.py:657`) não encontra o último aplicado e cai no fallback por relógio
   (`resolve_active` + `next_entry`, `__init__.py:693-695`).
2. Itens com `hora` ficam fora da ordem de avanço: `_rotation` (`config.py:726`)
   exclui quem tem `hora_start` e `_cycle_order` (`config.py:748`) é só
   rotação + defaults. `next_entry` (`config.py:1073`) procura o ativo por
   `(local, nome)` (`config.py:1092`); não achando (item de hora), retorna
   `rot[0]` (`config.py:1094`) — salta para o primeiro da rotação/default em vez do
   próximo slot de hora.
3. O avanço do `-n` não é adotado pela agenda: ele aplica direto e grava `set_last`
   (`__init__.py:710-712`), mas o daemon decide só por `resolve_active` (relógio);
   o wallpaper do `-n` vale até a próxima transição natural (o daemon não re-aplica
   o mesmo item porque a chave local dele já bate, mas também não incorpora a escolha).
4. Modo lista (`-a <lista>`): `_list_next` (`__init__.py:508`) aplica o próximo
   sub-item e incrementa `idx` no estado; `_run_list_cycle` (`daemon.py:183`) relê o
   cfg a cada volta (`daemon.py:192`) e respeita o novo idx — porém ao acordar troca
   imediatamente, cortando o tempo restante do sub atual. No modo mini-agenda
   (`_run_list_schedule`), vale o problema 2.

Comportamento esperado: `-n` após `-a` deve ir ao próximo wallpaper da agenda
(próximo slot de hora / próximo item da fila / próximo sub-item da lista), com o
avanço respeitado pelo daemon até a fronteira seguinte.

Mudanças necessárias (pendente):

- Persistir a posição de forma que o daemon respeite (ex.: `_run_schedule` gravar
  `set_last`, ou um override com validade até a próxima transição).
- `next_entry`: quando o ativo tem `hora`, avançar para o próximo slot
  (via `_hora_slots`/`next_transition`) em vez de cair em `rot[0]`.
- Definir no modo lista se o `-n` corta o tempo do sub atual ou só enfileira o próximo.

## Desenvolvimento

```sh
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]' pytest pyyaml   # ou: .venv/bin/pip install -e . pytest pyyaml
.venv/bin/pytest
```

O código vive em `src/wallp/`:
- `paths.py` — `DEFAULT_CONFIG`, `SALT_FILE`, `LOG_FILE`
- `log.py` — `_append_log`, `err`, `info`
- `parse.py` — `parse_tempo`, `parse_time`, `parse_hora`, `parse_loop`, `parse_dia`, `matches_day` etc.
- `media.py` — `WALLP_EXTS`, `video_duration`, `list_dir_files`, `get_salt`, `day_shuffled`
- `yt.py` — `yt_dir`, `download_yt`, `clean_yt_buffer` (`YT_CACHE_MB=500`, LRU)
- `randomcfg.py` — `build_random_queue`, `cfg_seconds`, `random_boundary`
- `entries.py` — `load`, `load_entries`, `find_list`, `format_entry`, `list_media_queue`
- `schedule.py` — `resolve_active`, `_hora_slots`, `_rotation` etc.
- `transitions.py` — `next_transition`, `next_entry`, `advance_in_list` etc.
- `apply.py` — backend DBus/Plasma (`apply`, `plugin_for`)
- `state.py` — estado (`auto`, `random`, `list`, `pos`, `last`)
- `cli.py` — `parse`, `help` (inclui `-x cache` e limite 500MB)
- `service.py` — `UNIT`, `_start_service`, `_stop_service`, `_show_log`
- `msgs.py` — `_fmt_secs`, `_fim_txt`
- `mode_random.py` / `mode_auto.py` / `mode_change.py` — dispatch do `main()`
- `daemon.py` + `daemon_list.py` / `daemon_random.py` / `daemon_schedule.py` — loop do daemon
- `config.py` — shim de compatibilidade re-exportando símbolos antigos