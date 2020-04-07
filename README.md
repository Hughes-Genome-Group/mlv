# mlv

Multi Locus View (MLV) is a web based tool for analysing and visualizing Next Generation Sequencing data sets.
By allowing intuitive filtering and visualization of multiple genomic locations, it allows the user to quickly drill
down and annotate regions of interest.

![Screen Shot](cover.png)

## Documenation

 * [Developer]() How to install MLV and extend its functionality
 * [User](https://lanceotron.readthedocs.io/en/latest/multi_locus_view/multi_locus_view.html) How to visualise  CHiP-seq/ATAC data

It is designed to extensible with stand alone modules. There are two other applications based on MLV:-

* [LanceOtron](https://lanceotron.molbiol.ox.ac.uk/) - Machine Learning to call peaks in CHiP-seq dataa 
* [CaptureSee](https://capturesee.molbiol.ox.ac.uk/) - Visualisation og highlu multiplexed CaptureSee experiments

The backend is written in python using the flask framweork and enables the running of pipelines either locally
or on remote servers


It is composed of two main JavaScript components

* [CIView](https://github.com/Hughes-Genome-Group/CIView) -Interactive charts/tables and images
* [MLVPanel](https://github.com/Hughes-Genome-Group/MLVPanel)
