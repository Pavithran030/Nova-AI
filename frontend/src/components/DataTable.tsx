import { ReactNode } from 'react';
import './DataTable.css';

interface Column {
  key: string;
  header: string;
  render?: (val: any, row: any) => ReactNode;
}

interface DataTableProps {
  columns: Column[];
  data: any[];
  onRowClick?: (row: any) => void;
}

const DataTable = ({ columns, data, onRowClick }: DataTableProps) => {
  return (
    <div className="table-container">
      <table className="custom-data-table">
        <thead>
          <tr>
            {columns.map(col => (
              <th key={col.key}>{col.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i} onClick={() => onRowClick?.(row)} className={onRowClick ? 'clickable' : ''}>
              {columns.map(col => (
                <td key={col.key}>
                  {col.render ? col.render(row[col.key], row) : row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default DataTable;
