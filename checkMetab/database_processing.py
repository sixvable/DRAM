from os import path, mkdir
from checkMetab.utils import run_process, merge_files, make_mmseqs_db
from datetime import datetime
from shutil import move, rmtree
from glob import glob


def get_iso_date():
    return datetime.today().strftime('%Y%m%d')


def download_file(url, output_file, verbose=True):
    if verbose:
        print('downloading %s' % url)
    run_process(['wget', '-O', output_file, url], verbose=verbose)


def download_and_process_unifref(output_dir, uniref_version='90', threads=10, verbose=True):
    """"""
    uniref_fasta_zipped = path.join(output_dir, 'uniref%s.fasta.gz' % uniref_version)
    uniref_url = 'ftp://ftp.uniprot.org/pub/databases/uniprot/uniref/uniref%s/uniref%s.fasta.gz' %\
                 (uniref_version, uniref_version)
    download_file(uniref_url, uniref_fasta_zipped, verbose=verbose)
    uniref_mmseqs_db = path.join(output_dir, 'uniref%s.%s.mmsdb' % (uniref_version, get_iso_date()))
    make_mmseqs_db(uniref_fasta_zipped, uniref_mmseqs_db, create_index=True, threads=threads, verbose=verbose)


def process_mmspro(full_alignment, output_dir, db_name='db', threads=10, verbose=True):
    mmseqs_msa = path.join(output_dir, '%s.mmsmsa' % db_name)
    run_process(['mmseqs', 'convertmsa', full_alignment, mmseqs_msa], verbose=verbose)
    mmseqs_profile = path.join(output_dir, '%s.mmspro' % db_name)
    run_process(['mmseqs', 'msa2profile', mmseqs_msa, mmseqs_profile, '--match-mode', '1', '--threads', str(threads)],
                verbose=verbose)
    tmp_dir = path.join(output_dir, 'tmp')
    run_process(['mmseqs', 'createindex', mmseqs_profile, tmp_dir, '-k', '5', '-s', '7', '--threads', str(threads)],
                verbose=verbose)
    return mmseqs_profile


def download_and_process_pfam(output_dir, pfam_release='32.0', threads=10, verbose=True):
    pfam_full_zipped = path.join(output_dir, 'Pfam-A.full.gz')
    download_file('ftp://ftp.ebi.ac.uk/pub/databases/Pfam/releases/Pfam%s/Pfam-A.full.gz' % pfam_release,
                  pfam_full_zipped)
    pfam_profile = process_mmspro(pfam_full_zipped, output_dir, 'pfam', threads, verbose)
    return pfam_profile


def download_and_process_dbcan(output_dir, dbcan_release='7', verbose=True):
    dbcan_hmm = path.join(output_dir, 'dbCAN-HMMdb-V%s.txt' % dbcan_release)
    download_file('http://bcb.unl.edu/dbCAN2/download/Databases/dbCAN-HMMdb-V%s.txt' % dbcan_release, dbcan_hmm,
                  verbose=verbose)
    run_process(['hmmpress', dbcan_hmm], verbose=verbose)
    return dbcan_hmm


def download_and_process_viral_refseq(output_dir, viral_files=3, threads=10, verbose=True):
    """Can only download newest version"""
    # download all of the viral protein files, need to know the number of files
    # TODO: Make it so that you don't need to know number of viral files in refseq viral
    viral_file_list = list()
    for number in range(viral_files):
        refseq_url = 'ftp://ftp.ncbi.nlm.nih.gov/refseq/release/viral/viral.%s.protein.faa.gz' % number
        refseq_faa = path.join(output_dir, 'viral.%s.protein.faa.gz' % number)
        download_file(refseq_url, refseq_faa)
        viral_file_list.append(refseq_faa)

    # then merge files from above
    merged_viral_faas = path.join(output_dir, 'viral.merged.protein.faa.gz')
    merge_files(viral_file_list, merged_viral_faas)

    # make mmseqs database
    refseq_viral_mmseqs_db = path.join(output_dir, 'refseq_viral.%s.mmsdb' % get_iso_date())
    make_mmseqs_db(merged_viral_faas, refseq_viral_mmseqs_db, create_index=True, threads=threads, verbose=verbose)
    return refseq_viral_mmseqs_db


def process_kegg_db(output_dir, kegg_loc, download_date=None, threads=10, verbose=True):
    if download_date is None:
        download_date = get_iso_date()
    kegg_mmseqs_db = path.join(output_dir, 'kegg.%s.mmsdb' % download_date)
    make_mmseqs_db(kegg_loc, kegg_mmseqs_db, create_index=True, threads=threads, verbose=verbose)
    return kegg_mmseqs_db


def prepare_databases(output_dir, kegg_loc=None, kegg_download_date=None, keep_database_files=False, threads=10,
                      verbose=True):
    mkdir(output_dir)
    temporary = path.join(output_dir, 'database_files')
    mkdir(temporary)
    output_dbs = list()
    if kegg_loc is not None:
        output_dbs.append(process_kegg_db(temporary, kegg_loc, kegg_download_date, threads, verbose))
    output_dbs.append(download_and_process_unifref(temporary, threads=threads, verbose=verbose))
    output_dbs.append(download_and_process_pfam(temporary, threads=threads, verbose=verbose))
    output_dbs.append(download_and_process_dbcan(temporary, verbose=verbose))
    output_dbs.append(download_and_process_viral_refseq(temporary, threads=threads, verbose=verbose))

    for output_db in output_dbs:
        for db_file in glob('%s*' % output_db):
            move(db_file, path.join(output_dir, path.basename(db_file)))

    if not keep_database_files:
        rmtree(output_dir)
