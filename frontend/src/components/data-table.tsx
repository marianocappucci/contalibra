import {
  type ColumnDef,
  type ColumnSizingState,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from '@tanstack/react-table'
import { useState, type ReactNode } from 'react'
import { ArrowUpDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'

// Wrapper generico sobre TanStack Table (logica de sorting + resize de
// columnas) + los primitivos de shadcn (presentacion) -- mismo patron que
// gestiolibra/frontend/src/components/data-table.tsx (DECISIONS.md
// ADR-026 de Gestiolibra), reusado tal cual en cada modulo migrado.
//
// Resize de columnas (arrastrar el borde del header, como Outlook/Excel):
// ancho de tabla = table.getTotalSize() (no 100%), columnas fijadas via
// <colgroup> + table-layout:fixed -- si la suma de columnas excede el
// contenedor, el overflow-x-auto ya presente en <Table> muestra scroll,
// igual que antes, pero ahora el usuario elige que columna agrandar en
// vez de que el achicado automatico por breakpoint decida por el.

declare module '@tanstack/react-table' {
  interface ColumnMeta<TData, TValue> {
    // Clase opcional para ocultar/priorizar columnas segun breakpoint,
    // ej. 'hidden md:table-cell' en columnas secundarias -- evita que
    // tablas con muchas columnas fuercen scroll horizontal en mobile.
    className?: string
  }
}

export function sortableHeader(label: string) {
  return ({ column }: { column: { toggleSorting: (desc?: boolean) => void; getIsSorted: () => false | 'asc' | 'desc' } }) => (
    <Button
      variant="ghost"
      size="sm"
      className="-ml-3 h-8"
      onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
    >
      {label}
      <ArrowUpDown className="ml-2 h-3.5 w-3.5" />
    </Button>
  )
}

type DataTableProps<TData, TValue> = {
  columns: ColumnDef<TData, TValue>[]
  data: TData[]
  emptyMessage?: ReactNode
  // Clase opcional por fila -- restaura el atenuado que las tablas Bootstrap
  // viejas aplicaban a filas inactivas (ej. `opacity-50` en clientes/list.html,
  // `table-secondary` en productos/list.html).
  getRowClassName?: (row: TData) => string | undefined
}

export function DataTable<TData, TValue>({
  columns, data, emptyMessage = 'Sin resultados.', getRowClassName,
}: DataTableProps<TData, TValue>) {
  const [sorting, setSorting] = useState<SortingState>([])
  const [columnSizing, setColumnSizing] = useState<ColumnSizingState>({})

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    columnResizeMode: 'onChange',
    onColumnSizingChange: setColumnSizing,
    state: { sorting, columnSizing },
  })

  return (
    <Table className="table-fixed" style={{ width: table.getTotalSize() }}>
      <colgroup>
        {table.getFlatHeaders().map((header) => (
          <col key={header.id} style={{ width: header.getSize() }} />
        ))}
      </colgroup>
      <TableHeader>
        {table.getHeaderGroups().map((headerGroup) => (
          <TableRow key={headerGroup.id}>
            {headerGroup.headers.map((header) => (
              <TableHead key={header.id} className={cn('relative select-none overflow-hidden', header.column.columnDef.meta?.className)}>
                {header.isPlaceholder
                  ? null
                  : flexRender(header.column.columnDef.header, header.getContext())}
                {header.column.getCanResize() && (
                  <div
                    onMouseDown={header.getResizeHandler()}
                    onTouchStart={header.getResizeHandler()}
                    onClick={(e) => e.stopPropagation()}
                    className={cn(
                      'absolute top-0 right-0 h-full w-2 cursor-col-resize touch-none select-none',
                      'after:absolute after:right-0 after:top-1 after:bottom-1 after:w-px after:bg-border hover:after:bg-primary',
                      header.column.getIsResizing() && 'after:bg-primary after:w-0.5',
                    )}
                  />
                )}
              </TableHead>
            ))}
          </TableRow>
        ))}
      </TableHeader>
      <TableBody>
        {table.getRowModel().rows.length ? (
          table.getRowModel().rows.map((row) => (
            <TableRow key={row.id} className={getRowClassName?.(row.original)}>
              {row.getVisibleCells().map((cell) => (
                <TableCell key={cell.id} className={cn('overflow-hidden', cell.column.columnDef.meta?.className)}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </TableCell>
              ))}
            </TableRow>
          ))
        ) : (
          <TableRow>
            <TableCell colSpan={columns.length} className="h-24 text-center text-sm text-muted-foreground">
              {emptyMessage}
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  )
}
