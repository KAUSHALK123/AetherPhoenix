import type { ArtifactItem } from '../types/artifact';

// Dedicated state and contract for generated artifacts
let cachedArtifacts: ArtifactItem[] = [
  {
    id: 'art-1',
    filename: 'Market_Research_Summary.pdf',
    type: 'PDF',
    size_bytes: 428000,
    status: 'READY',
    created_at: new Date(Date.now() - 3600000).toISOString(),
    workflow_id: 'wf-sample-1',
    task_id: 'task-101',
    download_url: '#',
    preview_content: 'Comprehensive Market Research Report detailing AI automation and competitive landscape.',
  },
  {
    id: 'art-2',
    filename: 'Quarterly_Executive_Pitch.pptx',
    type: 'PPTX',
    size_bytes: 1250000,
    status: 'READY',
    created_at: new Date(Date.now() - 7200000).toISOString(),
    workflow_id: 'wf-sample-1',
    task_id: 'task-102',
    download_url: '#',
    preview_content: 'Slide 1: Executive Overview\nSlide 2: Strategic Pillars\nSlide 3: Financial Projections & ROI',
  },
  {
    id: 'art-3',
    filename: 'Lead_Analysis_Dataset.csv',
    type: 'CSV',
    size_bytes: 85400,
    status: 'READY',
    created_at: new Date(Date.now() - 86400000).toISOString(),
    workflow_id: 'wf-sample-2',
    task_id: 'task-201',
    download_url: '#',
    preview_content: 'Company,Score,Industry,Contact\nAcme Corp,94,Technology,admin@acme.com\nGlobex,88,Logistics,sales@globex.org',
  },
];

export const artifactService = {
  async getArtifacts(): Promise<ArtifactItem[]> {
    return [...cachedArtifacts];
  },

  addArtifact(artifact: ArtifactItem) {
    cachedArtifacts = [artifact, ...cachedArtifacts];
  },
};
