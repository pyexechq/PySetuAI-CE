"use client";

import { useCallback, useMemo } from "react";
import { AgGridReact } from "ag-grid-react";
import {
  AllCommunityModule,
  ModuleRegistry,
  type ColDef,
  type GridApi,
  type GridReadyEvent,
} from "ag-grid-community";
import type { AuditLogEntry } from "@/lib/types/domain";

import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";

ModuleRegistry.registerModules([AllCommunityModule]);

interface AuditLogGridProps {
  rows: AuditLogEntry[];
  recentIds: Set<string>;
  quickFilterText?: string;
  onGridReady?: (api: GridApi<AuditLogEntry>) => void;
  onRowSelect?: (entry: AuditLogEntry | null) => void;
}

export function AuditLogGrid({ rows, recentIds, quickFilterText = "", onGridReady, onRowSelect }: AuditLogGridProps) {
  const columnDefs = useMemo<ColDef<AuditLogEntry>[]>(
    () => [
      {
        field: "timestamp",
        headerName: "Timestamp",
        filter: "agTextColumnFilter",
        width: 168,
        sort: "desc",
      },
      { field: "actor", headerName: "Actor", filter: "agTextColumnFilter", flex: 1, minWidth: 140 },
      { field: "action", headerName: "Action", filter: "agTextColumnFilter", flex: 1, minWidth: 130 },
      { field: "resource", headerName: "Resource", filter: "agTextColumnFilter", flex: 1, minWidth: 160 },
      {
        field: "status",
        headerName: "Status",
        filter: "agSetColumnFilter",
        width: 112,
        cellClass: (params) => `audit-status-cell audit-status-${params.value}`,
      },
      {
        field: "risk",
        headerName: "Risk",
        filter: "agSetColumnFilter",
        width: 96,
        valueFormatter: (params) =>
          params.value ? String(params.value).charAt(0).toUpperCase() + String(params.value).slice(1) : "",
        cellClass: (params) => `audit-risk-cell audit-risk-${params.value}`,
      },
      {
        field: "details",
        headerName: "Details",
        filter: "agTextColumnFilter",
        flex: 2,
        minWidth: 220,
        tooltipField: "details",
      },
    ],
    []
  );

  const defaultColDef = useMemo<ColDef>(
    () => ({
      sortable: true,
      resizable: true,
      filter: true,
    }),
    []
  );

  const getRowClass = useCallback(
    (params: { data?: AuditLogEntry }) => {
      if (!params.data) return undefined;
      const classes: string[] = [];
      if (params.data.status === "blocked") classes.push("audit-row-blocked");
      if (recentIds.has(params.data.id)) classes.push("audit-row-recent");
      return classes.join(" ");
    },
    [recentIds]
  );

  const handleGridReady = useCallback(
    (event: GridReadyEvent<AuditLogEntry>) => {
      onGridReady?.(event.api);
    },
    [onGridReady]
  );

  return (
    <div className="audit-log-grid ag-theme-quartz w-full rounded-md border border-border/60">
      <AgGridReact<AuditLogEntry>
        rowData={rows}
        columnDefs={columnDefs}
        defaultColDef={defaultColDef}
        animateRows
        pagination
        paginationPageSize={50}
        paginationPageSizeSelector={[25, 50, 100, 200]}
        quickFilterText={quickFilterText}
        getRowClass={getRowClass}
        suppressCellFocus
        onGridReady={handleGridReady}
        onRowClicked={(event) => onRowSelect?.(event.data ?? null)}
        domLayout="normal"
        rowHeight={44}
        headerHeight={42}
      />
    </div>
  );
}
