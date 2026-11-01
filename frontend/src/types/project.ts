export type RiskSeverity = 'low' | 'medium' | 'high' | 'critical';
export type RiskStatus = 'open' | 'mitigating' | 'closed';

export interface Project {
  id: number;
  organisation: number;
  name: string;
  risk_score: number;
  created_at: string;
  updated_at: string;
  open_risks_count?: number;
}

export interface Risk {
  id: number;
  project: number;
  title: string;
  description: string;
  severity: RiskSeverity;
  status: RiskStatus;
  owner: string;
  created_at: string;
  updated_at: string;
}

export interface UpdateRiskPayload {
  title?: string;
  description?: string;
  severity?: RiskSeverity;
  status?: RiskStatus;
  owner?: string;
}

export type CSVJobStatus = 'queued' | 'processing' | 'completed' | 'failed';

export interface CSVImportJob {
  id: string;
  job_id: string;
  project: number;
  project_name: string;
  filename: string;
  status: CSVJobStatus;
  total_rows: number;
  processed_rows: number;
  error_details: {
    errors?: string[];
    [key: string]: any;
  };
  created_by_email: string;
  created_at: string;
  updated_at: string;
}


