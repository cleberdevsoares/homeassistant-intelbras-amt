# Intelbras AMT (nuvem) para Home Assistant

Integração para centrais de alarme **Intelbras mais antigas** que são acessadas pelo app **AMT Mobile** através da nuvem da Intelbras (`amt.intelbras.com.br`). Essas centrais não abrem porta na rede local, então integrações locais (protocolo da porta 9009) não funcionam com elas.

> Projeto independente, sem vínculo com a Intelbras.

## Modelos

| Modelo | Situação |
|---|---|
| ANM 24 Net / ANM 24 Net G2 | testado |
| AMT 2018 / 2018 E / 2018 EG | experimental |
| AMT 2018 E Smart | experimental |
| AMT 4010 | experimental |

Para AMT 8000 e AMT 1016 NET existem outras integrações.

## O que ela traz

- **Painel de alarme** no Home Assistant: um por partição (A, B; C e D na AMT 4010) ou um único, se a central não for particionada
  - Estados: desarmado, armado, armado parcial (stay, nos modelos que têm) e disparado
  - Armar, armar parcial e desarmar pelo Home Assistant
- **Sirene disparada** (sensor binário)
- **Conectado à nuvem** (diagnóstico)
- **Firmware** da central (diagnóstico)

O estado é consultado a cada 30 segundos (ajustável nas opções da integração, mínimo de 10 s).

## Instalação (HACS)

1. HACS → menu ⋮ → **Repositórios personalizados**
2. Cole a URL deste repositório e escolha o tipo **Integração**
3. Procure **Intelbras AMT (nuvem)** no HACS e instale
4. Reinicie o Home Assistant
5. **Configurações → Dispositivos e serviços → Adicionar integração → Intelbras AMT (nuvem)**
6. Informe:
   - **MAC da central**: aparece no app AMT Mobile ao editar a central, ou na etiqueta do módulo Ethernet
   - **Senha remota**: a mesma usada no app
   - **Modelo**

A integração conecta na hora para conferir a senha e o modelo antes de salvar.

## Avisos

- Depende da nuvem da Intelbras. Se o servidor da Intelbras estiver fora, a integração fica indisponível.
- A central atende um aparelho por vez. Se o app AMT Mobile estiver aberto no celular, o Home Assistant pode receber "outro aparelho conectado" até o app ser fechado (e vice-versa).
- A senha fica guardada na configuração do Home Assistant, então armar e desarmar pelo HA não pede código. Se quiser exigir confirmação, use um script ou uma automação com condição.
