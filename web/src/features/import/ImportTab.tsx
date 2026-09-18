import { useRef, useState } from 'react'

import type { ModalityConfig } from '@/config/modalities'
import { ApiError } from '@/shared/api/client'
import { useDraws, useImportBatches, useImportDraws } from '@/shared/hooks/queries'
import { formatDate, formatDateTime, formatNumber } from '@/shared/lib/format'
import { NumberBall } from '@/shared/ui/NumberBall'
import { Alert, EmptyState, Panel, Spinner } from '@/shared/ui/primitives'

export function ImportTab({ config }: { config: ModalityConfig }) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const importMutation = useImportDraws(config.key)
  const batches = useImportBatches(config.key)
  const draws = useDraws(config.key, 10)

  const error = importMutation.error instanceof ApiError ? importMutation.error : null

  function send(file: File | undefined) {
    if (file) importMutation.mutate(file)
  }

  return (
    <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
      <div className="space-y-5">
        <Alert tone="warning" title="A importacao substitui todo o historico desta modalidade">
          O arquivo e validado por inteiro antes de qualquer escrita. Passando na validacao, os
          concursos de {config.label} sao apagados e substituidos pelos do arquivo, na mesma
          transacao. As outras modalidades nao sao tocadas. Se houver qualquer erro de validacao,
          nada e apagado.
        </Alert>

        <div
          onDragOver={(event) => {
            event.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault()
            setDragging(false)
            send(event.dataTransfer.files[0])
          }}
          className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-12 text-center transition ${
            dragging ? 'border-mod bg-[color-mix(in_oklab,var(--mod)_10%,transparent)]' : 'border-line bg-surface-1 hover:border-ink-3'
          }`}
        >
          <p className="text-base font-semibold text-ink-2">
            Arraste a planilha oficial da Caixa
          </p>
          <p className="mt-1 text-sm text-ink-3">Aceita .xlsx e .csv</p>
          <button
            type="button"
            className="btn-primary mt-5"
            onClick={() => inputRef.current?.click()}
            disabled={importMutation.isPending}
          >
            {importMutation.isPending ? 'Importando' : 'Escolher arquivo'}
          </button>
          <input
            ref={inputRef}
            type="file"
            accept=".xlsx,.xlsm,.csv"
            className="hidden"
            onChange={(event) => send(event.target.files?.[0])}
          />
        </div>

        {error ? (
          <Alert tone="danger" title={error.problem?.title ?? 'Falha na importacao'}>
            <p>{error.message}</p>
            {error.rowErrors.length ? (
              <div className="scroll-area mt-3 max-h-64 rounded-lg border border-[color-mix(in_oklab,var(--neg)_40%,transparent)] bg-surface-1">
                <table className="w-full text-left text-xs">
                  <thead className="sticky top-0 z-10 bg-[color-mix(in_oklab,var(--neg)_12%,transparent)] text-neg">
                    <tr>
                      <th className="px-3 py-2 font-semibold">Linha</th>
                      <th className="px-3 py-2 font-semibold">Campo</th>
                      <th className="px-3 py-2 font-semibold">Problema</th>
                    </tr>
                  </thead>
                  <tbody>
                    {error.rowErrors.map((row, index) => (
                      <tr key={`${row.row}-${index}`} className="border-t border-[color-mix(in_oklab,var(--neg)_22%,transparent)]">
                        <td className="px-3 py-2 font-mono">{row.row}</td>
                        <td className="px-3 py-2">{row.field}</td>
                        <td className="px-3 py-2">{row.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </Alert>
        ) : null}

        {importMutation.isSuccess ? (
          <Alert tone="success" title="Importacao concluida">
            <dl className="mt-2 grid gap-x-6 gap-y-1.5 sm:grid-cols-2">
              <Row label="Linhas importadas">
                {formatNumber(importMutation.data.rows_imported)}
              </Row>
              <Row label="Concursos apagados">
                {formatNumber(importMutation.data.rows_deleted)}
              </Row>
              <Row label="Faixa">
                {importMutation.data.first_contest} a {importMutation.data.last_contest}
              </Row>
              <Row label="Periodo">
                {formatDate(importMutation.data.first_drawn_at)} ate{' '}
                {formatDate(importMutation.data.last_drawn_at)}
              </Row>
              <Row label="sha256">
                <span className="font-mono text-[11px]">
                  {importMutation.data.file_hash.slice(0, 32)}
                </span>
              </Row>
            </dl>
          </Alert>
        ) : null}

        <Panel
          title="Previa do historico"
          hint="Os dez concursos mais recentes ja importados"
          scroll
        >
          {draws.isLoading ? <Spinner /> : null}
          {draws.data?.items.length ? (
            <table className="w-full text-left text-sm">
              <thead className="table-head-sticky">
                <tr>
                  <th className="px-1 pb-2 pt-0">Concurso</th>
                  <th className="px-1 pb-2 pt-0">Data</th>
                  <th className="px-1 pb-2 pt-0">Dezenas</th>
                </tr>
              </thead>
              <tbody>
                {draws.data.items.map((draw) => (
                  <tr key={draw.contest_no} className="table-row">
                    <td className="whitespace-nowrap px-1 py-2 font-semibold text-ink-2">
                      {draw.contest_no}
                    </td>
                    <td className="whitespace-nowrap px-1 py-2 text-xs text-ink-3">
                      {formatDate(draw.drawn_at)}
                    </td>
                    <td className="px-1 py-2">
                      <span className="flex flex-wrap gap-1">
                        {draw.numbers.map((value, index) => (
                          <NumberBall
                            key={`${draw.contest_no}-${index}`}
                            value={value}
                            size="sm"
                            padded={config.boardKind !== 'columns'}
                          />
                        ))}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : draws.isLoading ? null : (
            <EmptyState
              title="Nenhum concurso importado"
              description="Envie a planilha para comecar."
            />
          )}
        </Panel>
      </div>

      <Panel
        title="Historico de importacoes"
        hint="Cada envio fica registrado com o hash do arquivo"
        className="xl:sticky xl:top-6"
        bodyClassName="max-h-[560px]"
        scroll
      >
        {batches.isLoading ? <Spinner /> : null}
        {batches.data?.length ? (
          <ul className="space-y-3">
            {batches.data.map((batch) => (
              <li key={batch.id} className="border-b border-line-soft pb-3 last:border-0 last:pb-0">
                <p className="truncate text-sm font-semibold text-ink-2" title={batch.filename}>
                  {batch.filename}
                </p>
                <p className="mt-0.5 text-xs text-ink-3">
                  {formatNumber(batch.rows_imported)} concursos, de {batch.first_contest} a{' '}
                  {batch.last_contest}
                </p>
                <p className="text-xs text-ink-3">{formatDateTime(batch.imported_at)}</p>
              </li>
            ))}
          </ul>
        ) : batches.isLoading ? null : (
          <EmptyState title="Sem importacoes registradas" />
        )}
      </Panel>
    </div>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-2">
      <dt className="shrink-0 text-[color-mix(in_oklab,var(--pos)_70%,transparent)]">{label}:</dt>
      <dd className="min-w-0 font-semibold">{children}</dd>
    </div>
  )
}
