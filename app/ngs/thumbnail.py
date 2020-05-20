from app.ngs.view import ViewSet
from app.ngs.utils import get_temporary_folder
from app import app,db,databases
from app.ngs.gene import get_genes,get_genes_in_view_set
from app.ngs.track import add_track_details
from PIL import ImageFont
from PIL import Image, ImageDraw
import math
import os
import ujson
from pathlib import Path
from requests.utils import requote_uri
from urllib.request import urlretrieve

import pyBigWig
import time


class ThumbnailSet(object):
    def __init__(self,db,tracks=[],annotation_sets=None,
             gene_set=0,height=150,width=300,scale=True,
             auto_layout=True):
        '''
        
        Args:
            tracks (Optional[List[dict]]): A list of configs describing
               the tracks to be included in the thumbnail
            annotation_sets (Optional[List[int]]): A list of annotation set ids
               to be included in the thumbnail
            gene_set (Optional[boolean]): Default True - include the default gene set in
               any thumbnails.If many thumbnails are going to be produced. It is more efficient
               to retreive all genes at once and pass the relevent ones to the draw method
            height (int) The height of the thumbnail - default 100
            width (int) The width of the thumbnail - default 200
        '''
        self.width=width
        self.height=height
        self.db=db
        self.annotation_sets=annotation_sets
        self.gene_set=gene_set
        self.scale =scale
        self.tracks=[]
        self.track_dict={}
        self.label_font  = ImageFont.truetype(app.config['IMAGE_FONT'],11)
      
        #sort out tracks
        self.add_tracks(tracks)
        
        if auto_layout:
            self._auto_layout()
            
        
    def add_tracks(self,configs):
        '''Adds tracks to draw in the thumbnail
        Args:
            configs(list[dict]) A list of dictionary objects describing
                each track
        
        '''   
        for config in configs:
            track=None
            if config['url'].endswith(".bw") or config.get("type") == "bigwig":
                track=WigTrack(config,self.width)
            if config['url'].endswith(".bb"):
                track=BedTrack(config,self.width)
            self.tracks.append(track)
            self.track_dict[config['track_id']]=track
            
        for track in self.tracks:
            if hasattr(track,"scale_link_to"):
                if track.scale_link_to:
                    track.scale_link_to=self.track_dict[track.scale_link_to]
        
    def _auto_layout(self,annotations=None,genes=False):
        '''Will try and layout the tracks depending on their preferred
        height (specified in the config). Genes have a preferred height
        of 40px and 20px for each annotation set
        If annotations and genes are being added separately (e.g,  from a
        view set, where they are all calulated at once to prevent multiple
        calls to the database), the genes and annotations arguments should be 
        supplied. Otherwise these are calculated from the Thumbnail set's
        own properties
        Args:
            annotations (Optional[int]): The number of annotations in the
                the thumbnial (0 by default)
            genes (Optional[boolean]): Whether genes are added to the 
                the thumbnail (False by default)
        
        '''
        order = ["scale","gene_set","annotation_sets","tracks"]
        components={}
        total=0
        if self.gene_set or genes:
            components['gene_set']={"preferred":40}
            total+=40
        if self.annotation_sets or annotations:
            if self.annotation_sets:
                ann_len= len(self.annotation_sets)
            else:
                ann_len= len(annotations)
            components['annotation_sets']={"preferred":ann_len*20}
            total+=ann_len*20
        if self.scale:
            total+=20
            components['scale']={"preferred":20}
        t_height=0      
        for track in self.tracks:
            if not track.draw_on:
                t_height+=track.height
           
        if t_height:
            if t_height<self.height-total:
                t_height=self.height-total
            components['tracks']={"preferred":t_height}
            total+=t_height    
                    
        for comp in components:
            info = components[comp]
            info['calculated']=int((info['preferred']/total)*self.height)
            #tracks can be bigger than preferred - take up rest of height
            if info['calculated']>info['preferred'] and comp != "tracks":
                info['calculated']=info['preferred']
       
      
            
        y_pos=0   
        for  item in order:
            info= components.get(item)
            if not info:
                continue
            if item=="scale":
                self._calculate_scale(info['calculated'],y_pos)
                y_pos+=info['calculated']
            elif item=="gene_set":
                self._calculate_genes(info['calculated'],y_pos)
                y_pos+=info['calculated']
            elif item=="annotation_sets":       
                self._calculate_annotations(info['calculated'],y_pos,annotations=annotations)
                y_pos+=info['calculated']
            
            
        if t_height:
            total_track_height = components['tracks']['calculated']
            remaining_height=total_track_height
            wig_track_heights=0
            for track in self.tracks:
                if track.draw_on:
                    continue
                if track.type=="wig":
                    wig_track_heights+=track.height
                    continue
                track.height= int((track.height/t_height)*total_track_height)
                if track.height>20:
                    track.height=20
                
                remaining_height-=track.height
                
            
            for track in self.tracks:
                if track.type=="bed":
                    continue
                track.height=int((track.height/wig_track_heights)*remaining_height)
            
              
            for track in self.tracks:
                if track.draw_on:
                    other_track=self.track_dict[track.draw_on]
                    track.top =other_track.top
                    track.height= other_track.height
                
                else:   
                    track.top =y_pos
                    y_pos+=track.height
                    if track.stretch_to_top:
                        track.top=25
                        track.height=y_pos-25
                
               
                font_size=int(track.height/2)
                if track.type=="wig":
                    font_size=int(track.height/4)
                if font_size>12:
                    font_size=12
                track.font  = ImageFont.truetype(app.config['IMAGE_FONT'],font_size)
                    
                   
        
            
    
    def _calculate_scale(self,height,y_pos):
        self.scale_height=height
        self.scale_y_pos=y_pos
        font_size= int((self.scale_height)/2)
        self.scale_font= ImageFont.truetype(app.config['IMAGE_FONT'],font_size)
        
           
    
    def _calculate_genes(self,height,y_pos):
        self.gene_height=height
        self.gene_y_pos=y_pos
        each_height = int(self.gene_height/4)

        font_size= each_height
        
        self.gene_font=ImageFont.truetype(app.config['IMAGE_FONT'],font_size)
        self.gene_info_1={"text_pos":self.gene_y_pos,"rec_top":self.gene_y_pos+each_height+2,
                          "line_pos":self.gene_y_pos+int(1.5*each_height),
                          "rec_bot":self.gene_y_pos+(2*each_height)-2}
        self.gene_info_2={"text_pos":self.gene_y_pos+(3*each_height),
                          "line_pos":self.gene_y_pos+int(2.5*each_height),
                          "rec_top":self.gene_y_pos+(2*each_height)+2,
                          "rec_bot":self.gene_y_pos+(3*each_height)-2}
    
    
         
    def _calculate_annotations(self,height,y_pos,annotations=None):
        if not annotations:
            annotations=self.annotation_sets
        number  = len(annotations)
        self.annotations_height=height
        self.annotations_y_pos=y_pos

       
        each_height = int(self.annotations_height/number)
        self.annotations_rec_height=int(each_height/2)
        font_size= int((each_height)/2)
        self.annotation_font=ImageFont.truetype(app.config['IMAGE_FONT'],font_size)
        as_details =  get_all_annotation_sets(self.db,annotations)
        details={}
        y_pos= self.annotations_y_pos
        for ad in as_details:
            
            config = {"name":ad['name'],"text_y_pos":y_pos,"color":"black"}        
            config["rec_y_pos_1"]=y_pos+int(each_height/2)+1
            config["rec_y_pos_2"]=y_pos+each_height-1
            details[ad['id']]=config
            y_pos+=each_height
        self.annotation_details=details
        
        
        
    
    
    def draw_view_set(self,view_set,gene_set=0,show_feature=True,
                      composite=False,specific_views=None,folder="thumbnails",job=None):
        '''Draws thumbnails for all the views in the set provided
        Args:
            view_set_id (ViewSet): The ViewSet object from which to 
                create the thumbnails
            gene_set(Optional[int]) The id of the the gene set to include
                in the thumbnails = default is 0 (None)
            show_feature(Optional[boolean]) If True (default) and the view
               set has margins of greater than one then tramlines will be drawn
               highlighting the feature
            composite:if supplied then this in addition to the  
            specific_views (Oprional[list]) - If given, then only the supplied
                ids will be drawn
            folder (Optional[str]) The folder where to save the thumbnails (named tn<id>)
               default is thumbnails
                
        '''
        import time
        #get the track details
        tracks=[]
        tracks.append(view_set.data.get("primary_track"))
        tracks=tracks +view_set.data.get("secondary_tracks")
        self.add_tracks(tracks)
        
        views = view_set.get_all_views(location_only=True,specific_views=specific_views)
        if not folder.startswith("/"):
            folder =view_set.get_folder(folder)
        margin1=view_set.data.get("margin")
        margin2=margin1
        t= time.time()
        vs_genes={}
        genes=False
        
        tn_det= view_set.data.get("thumbnail_details")
        absolute=False
        
        if tn_det:
            if tn_det.get("double_view"):
                margin2=int(tn_det.get("margin2"))
                composite=True
            else:
                margin1 = int(tn_det.get("margin"))
                margin2=margin1
            
        
        if gene_set:
            vs_genes = get_genes_in_view_set(view_set,unique_only=True,margin=margin2,
                                             specific_views=specific_views)
            genes=True
        an_sets= view_set.data.get("annotation_sets")
        anno_sets={}
        if an_sets and len(an_sets)!=0:
            anno_sets= get_annotations_in_view_set(view_set,an_sets,margin=margin2,
                                                   specific_views=specific_views)
       
        self._auto_layout(annotations=an_sets,genes=genes)   
        tram_lines=None
       
        
        if not composite:
            for vs in views:
                stub = "tn"+str(vs['id'])
                genes = vs_genes.get(vs['id'])
                annotations= anno_sets.get(vs['id'])
                if show_feature:
                    tram_lines=[vs['start'],vs['finish']]
                self.draw_thumbnail(vs['chromosome'],vs['start']-margin1,
                                    vs['finish']+margin1,folder,stub,
                                    genes=genes,annotations=annotations,tram_lines=tram_lines)
                if vs['id'] % 200 ==0:
                    print (str(vs['id'])+":"+str(((time.time()-t)/1000)))
                    if job:
                        job.status = "Creating Thumbnails {}/{}".format(vs['id'],len(views))
                        db.session.commit()
            
        else:
            for vs in views:
                stub = "tn"+str(vs['id'])
                genes = vs_genes.get(vs['id'])
                annotations= anno_sets.get(vs['id'])
                if show_feature:
                    tram_lines=[vs['start'],vs['finish']]
                    
                locations=[
                    {"chrom":vs['chromosome'],"start":vs['start']-margin1,"end":vs['finish']+margin1,'tram_lines':tram_lines},
                    {"chrom":vs['chromosome'],"start":vs['start']-margin2,"end":vs['finish']+margin2,'tram_lines':tram_lines}   
                ]
                self.draw_composite_thumbnail(locations, folder, stub,
                                    genes=genes,annotations=annotations)
                if vs['id'] % 200 ==0:
                    print (str(vs['id'])+":"+str(((time.time()-t)/1000)))
                    if job:
                        job.status = "Creating Thumbnails {}/{}".format(vs['id'],len(views))
                        db.session.commit()
        
        
        
    def _draw_annotations(self,draw,start,finish,annotations):
        bp_per_pixel = (finish-start)/self.width
        
        for id in self.annotation_details:
            a=self.annotation_details[id]
            draw.text((3,a['text_y_pos']),a['name'],"black",font=self.annotation_font)
        
        for anno in annotations:
            info= self.annotation_details[anno['annotation_set_id']]
                    
            st,en=self._get_coords(anno['start'],anno['finish'],start,finish,bp_per_pixel)
            draw.rectangle([st,info['rec_y_pos_1'],en,info['rec_y_pos_2']],fill=info['color'])
    
    
       
    def _draw_genes(self,draw,start,finish,gene_data):
        gene_data.sort(key=lambda g:g['start'] )
        bp_per_pixel = (finish-start)/self.width
        toggle =True
        for gene in gene_data:
            if toggle:
                pos=self.gene_info_1
            else:
                pos=self.gene_info_2
            toggle = not toggle
           
            st,en=self._get_coords(gene['start'],gene['end'],start,finish,bp_per_pixel)
            draw.line((st,pos['line_pos'],en,pos['line_pos']),fill="black")
            draw.text((st,pos['text_pos']),gene['name'],"black",font=self.gene_font)
            for exon in gene['exons']:
                st,en=self._get_coords(int(exon['start']),int(exon['end']),start,finish,bp_per_pixel)
                draw.rectangle([st,pos['rec_top'],en,pos['rec_bot']],fill="black")
          
          

    
          
         
    def _draw_scale(self,draw,start,finish):
        bp_per_pixel=(finish-start)/self.width
        range = math.floor(1100*bp_per_pixel)
        majorTick,majorUnit,unitMultiplier=self._findSpacing(range)
        spacing = majorTick
        nTick = math.floor(start / spacing) - 1
        x = 0;
        y_pos=self.scale_y_pos
        draw.line((0,y_pos+self.scale_height,self.width,y_pos+self.scale_height),fill="black")
        while x<self.width:
            l = math.floor(nTick * spacing)
            x = round(((l - 1) - start + 0.5) / bp_per_pixel)
            draw.line((x,y_pos+self.scale_height/2,x,y_pos+self.scale_height),fill="black")
            label =str(str(int(l / unitMultiplier)))+majorUnit
            draw.text((x-4,self.scale_y_pos),label,"black",font=self.scale_font)  
            nTick+=1           
   

    def _findSpacing(self,maxValue) :

        if maxValue < 10: 
            return 1, "", 1
        
        nZeroes = math.floor(math.log10(maxValue))
        majorUnit = ""
        unitMultiplier = 1
        if nZeroes > 9: 
            majorUnit = "gb"
            unitMultiplier = 1000000000
        
        if nZeroes > 6:
            majorUnit = "mb"
            unitMultiplier = 1000000
        elif nZeroes > 3:
            majorUnit = "kb"
            unitMultiplier = 1000
        

        nMajorTicks = maxValue / math.pow(10, nZeroes - 1);
        if nMajorTicks < 25:
            return math.pow(10, nZeroes - 1), majorUnit, unitMultiplier
        else:
            return math.pow(10, nZeroes) / 2, majorUnit, unitMultiplier
        

      
          
            
    def _get_coords(self,st,en,start,finish,bp_per_pixel):
        st1 = (st-start)/bp_per_pixel
        if st1<0:
            st1=0
        en1 = (en-start)/bp_per_pixel
        if en1 > self.width:
            en1=self.width
        return st1,en1
        
    
    def draw_composite_thumbnail(self,locations,folder,stub,genes=None,annotations=None):
        
        im = Image.new('RGBA', (self.width,(self.height*2)+27), "white")
        y=0
        x=0
        for loc in locations:
            if self.gene_set:
                genes = get_genes(self.db,loc['chrom'],loc['start'],loc['end'],self.gene_set,unique_only=True)
            if self.annotation_sets:
                annotations=get_all_annotations(self.db,loc['chrom'],loc['start'],loc['end'],set_ids=self.annotation_sets)
      
            tmb = self.draw_thumbnail(loc['chrom'],loc['start'],loc['end'],genes=genes,
                                      annotations=annotations,tram_lines=loc['tram_lines'])
            
            im.paste(tmb,(x,y+12))
            y+=self.height+15
        file_name= os.path.join(folder,stub+".png")
        draw= ImageDraw.Draw(im)
        draw.text((10,0),"ZOOMED IN","black",font=self.label_font)
        draw.rectangle([(0,self.height+12),(self.width,self.height+15)],fill="black")
        draw.text((10,self.height+15),"ZOOMED OUT","black",font=self.label_font)
        im.save(file_name)
         
        
    
    
    
    
    def draw_thumbnail(self,chr,start,end,
                       folder=None,stub=None,
                       genes=None,annotations=None,
                       tram_lines=None):
        '''Draws the thumbnail for the given range and saves it to
        the file specified by folder and stub, if a folder name is
        given
    
        Args:
            chr (str): The name of the chromosome (e.g. 'chr12')
            start (int): The start of the range
            end (int): The end of the range
            folder(Optional[str]): The folder to save the thumbnail
            stub(Optional[str]): The name of the thumbnail
            genes(Optional[list): A list of genes to draw, not required
                If a gene set was specified when creating the Thumbnail object
            annotations(Optional[list]):A list of annotations to draw, 
                not required if annotations were specified in object creation
            tram_lines(list[int]): Optional - an array containing start and stop
                co-ordinates of tramlines to draw to show a feature
        
        Returns:
            The image object
        '''
        
        im = Image.new('RGBA', (self.width,self.height), "white")
        canvas = ImageDraw.Draw(im)
       
        for track in self.tracks:
            track.draw(canvas,chr,start,end)
        if self.gene_set:
            genes = get_genes(self.db,chr,start,end,self.gene_set,unique_only=True)
        if genes:
            self._draw_genes(canvas,start,end,genes)
        if self.annotation_sets:
            annotations=get_all_annotations(self.db,chr,start,end,set_ids=self.annotation_sets)
        if annotations:
            self._draw_annotations(canvas,start,end,annotations)
        if self.scale:
            self._draw_scale(canvas,start,end)  
        if tram_lines:
            st,en=self._get_coords(tram_lines[0],tram_lines[1],start,end,(end-start)/self.width)
            canvas.line((st,0,st,self.height),fill=(0,0,0,64))
            canvas.line((en,0,en,self.height),fill=(0,0,0,64))
        if folder:
            file_name= os.path.join(folder,stub+".png")
            im.save(file_name)
        return im
    
    
class Track(object):
     def __init__(self,config,img_width):
        
        from PIL import ImageFont
        self.url=config['url']
     
        self.bw_reader= pyBigWig.open(config['url'])
        self.chroms=self.bw_reader.chroms()
        self.scale = config.get("scale","automatic")
        self.max_y=float(config.get("max_y",0))
        self.color=config.get("color","black")
        self.top=config.get("top",0)
        self.width=img_width
        self.show_label = config.get("show_label")
        self.name=config.get("short_label","")
        self.draw_on=config.get("draw_on")
        self.stretch_to_top=config.get("stretch_to_top")
        self.number_drawn=0
        
       
             
            
        self.font  = ImageFont.truetype(app.config['IMAGE_FONT'],int(self.height/2))
        

    
class WigTrack(Track):
    '''Creates a track object used to draw the thumbnail
    Args:
        config(dict): A dictionary describing the track
        img_width(int): The width of the image
    
    '''
    def __init__(self,config,img_width):
        self.type="wig"
        self.height = config.get("height",50)
        self.line=False
        if config.get("display")=="line":
            self.line=True
        self.scale_link_to=config.get("scale_link_to")
       
        
        super().__init__(config,img_width)
        
     
    def draw(self,draw,chr,start,finish):
        self.number_drawn+=1
        ##only required for external wigs
        #if self.number_drawn%5==0:
        #    self.bw_reader.close()
        #    self.bw_reader = pyBigWig.open(self.url)
            
        start=start-1
        r_start=start
        r_end=finish

        
        if start<0:
            r_start=0
        chr_len = self.chroms.get(chr)
        if not chr_len:
            return

        if finish >= chr_len:
            r_end = chr_len-1
        
        bins=self.width
        draw_start=1
        if r_start!=start or r_end != finish:
            range= finish-start
            bins =int(((r_end-r_start)/range)*self.width)
            if r_start!=start:
                draw_start= int((start/range)*self.width)*-1
        
        try:
            data= self.bw_reader.stats(chr,r_start,r_end,nBins=bins)
        except:
            return
      
       
        max_h=0
        vals=[]
        for i in data:
            if not i:
                i=0
            if i>max_h:
                max_h=i
            vals.append(i)
        if not self.scale=="automatic":
            max_h = self.max_y  
        elif max_h==0:
            max_h=1
        if self.scale_link_to:
            max_h=self.scale_link_to.max_y
        self.max_y=max_h
        y_to = self.top+self.height
        prev_x=None
        prev_y=None
        for x,val in enumerate(vals,start=draw_start):
            y=self.height-((val/max_h)*self.height)
            if y<0:
                y=0
            y+=self.top
            if self.line:
                if prev_x !=None:
                    draw.line((prev_x,prev_y,x,y),fill=self.color)
                prev_x=x
                prev_y=y
            else:
                draw.line((x,y, x,y_to), fill=self.color)
        if not self.scale_link_to:  
            draw.line((self.width-10,self.top,self.width,self.top),fill='black')
            max_text=str(int(max_h))
            t_w,t_h= draw.textsize(max_text,self.font)
            draw.text((self.width-10-t_w,self.top-(t_h/2)),max_text,font=self.font,fill="black")
    
class BedTrack(Track):
    def __init__(self,config,img_width):
        self.type="bed"
        self.height=config.get("height",20)
        self.draw_on=False
        super().__init__(config,img_width)
        
    def draw(self,draw,chr,start,finish):
        r_start=start
        r_end=finish
        if start<0:
            r_start=0
        if finish >= self.chroms[chr]:
            r_end = self.chroms[chr]-1
        bp_per_pixel = (finish-start)/self.width
        draw.text((0,self.top),self.name,"black",font=self.font)
        data = self.bw_reader.entries(chr,r_start,r_end)
        if not data:
            return
        for item in data:
            st = (item[0]-start)/bp_per_pixel
            if st<0:
                st=0
            en = (item[1]-start)/bp_per_pixel
            if en > self.width:
                en=self.width
            draw.rectangle([st,(int(self.top+self.height/2))+1,en,self.top+self.height-1],fill=self.color)




def create_sprite_sheets(vs,sheet_dim=[8192,8192],factor=4):
    num = vs.get_view_number()['count']
    folder = vs.get_folder("thumbnails")
    
    
    im = Image.open(os.path.join(folder,"tn1.png"))
    size = im.size
    t_width = math.floor(size[0]/factor)
    t_height=math.floor (size[1]/factor)
    cols = math.floor(sheet_dim[0]/t_width)
    rows=math.floor(sheet_dim[1]/t_height)
    per_sheet= rows*cols
    sheet_dim=[cols*t_width,rows*t_height] 
    sheet_index=0
    sheet = Image.new('RGBA', (sheet_dim[0],sheet_dim[1]), "white")
    row=0
    col=0
    for n in range(1,num+1):
        im =Image.open(os.path.join(folder,"tn{}.png".format(n)))
        im.thumbnail((t_width,t_height))
        sheet.paste(im,(col*t_width,row*t_height))
        if  n==num:
            sheet.save(os.path.join(folder,"sprite_sheet{}.png".format(sheet_index)))
            break
        
        col+=1
        if col==cols:
            col=0
            row+=1
            if row==rows:
                sheet.save(os.path.join(folder,"sprite_sheet{}.png".format(sheet_index)))
                sheet_index+=1
                sheet=None
                sheet= Image.new('RGBA', (sheet_dim[0],sheet_dim[1]), "white")
                row=0
    sheet_urls=[];
    for n in range(0,sheet_index+1):
        sheet_urls.append("/data/{}/view_sets/{}/thumbnails/sprite_sheet{}.png".format(vs.db,vs.id,n))
    inf= {"sheets":sheet_urls,"rows":rows,"cols":cols,"number":num}         
    vs.set_data("sprite_sheets",inf)
    return  {
        "height":t_height,
        "width":t_width
        
    }  
def create_thumbnails_from_mlv(tracks,viewset,job=None,margins=0,image_width=300,step=50):
    total = viewset.get_view_number()["count"]
    folder =  viewset.get_folder("thumbnails")
    for track in tracks:
        url = track.get("url")
        if url:
            if url.startswith("/"):
                 track["url"]="https://lanceotron.molbiol.ox.ac.uk"+url
            
            
    config={
        "width":image_width,
        "height":200,
        "folder":folder,
        "fixed_height_mode":True,
        "background_color":"#FFFFFF" 
    }
    
    images=[]
    for n in range(0,total,step):
        sql = "SELECT id,chromosome,start,finish FROM {} ORDER BY id OFFSET {} LIMIT {}"\
        .format(viewset.table_name,n,step)
        locations = databases[viewset.db].execute_query(sql)
        images=[]
        for view in locations:
            start= view["start"]-margins
            end=  view["finish"]+margins
            images.append({
                "loc":[view["chromosome"],start,end],
                "stub":"tn{}".format(view["id"])
            })
    
        create_node_thumbnail(tracks,images,config)
        msg = "{}/{} images".format(n+step,total)
        print (msg)
        if job:
            if job.status=="failed":
                job.outputs=dict(job.outputs)
                job.outputs["uploaded_images"]=n+step
                db.session.commit()
                raise Exception("Job killed by user")
            job.status=msg
            db.session.commit()
    
   
               
            
                        
        
def create_node_thumbnail(tracks,images,config):
    folder = config.get("folder")
    if not folder:       
        folder = get_temporary_folder()
        config["folder"]=folder
    out_config = os.path.join(folder,"config.json")
    config["images"]=images
    json = ujson.dumps({
        "tracks":tracks,
        "config":config
    })
    out = open(out_config,"w")
    out.write(json)
    out.close()
    app_root= Path(app.root_path).parent
    os.environ["NODE_PATH"]="/usr/local/lib/node_modules"
    cmd = "node {}/node/image_gen.js {}/config.json".format(app_root,folder)
    os.system(cmd)
    return folder
        
       
def create_thumbnails_from_ucsc(url,viewset,job=None,margins=0,pixels=800,delay=3):
    views = viewset.get_all_views(location_only=True)
    folder =  viewset.get_folder("thumbnails")
    url= url.replace("hgTracks","hgRenderTracks");
    if "/s/" in url:
        arr=url.split("/")
        url = arr[0]+"//"+arr[2]+"/cgi-bin/hgRenderTracks?hgS_doOtherUser=submit&hgS_otherUserName="+arr[4]+"&hgS_otherUserSessionName="+arr[5]
    failiures=0  
    for count,view in enumerate(views,start=1):
        to_get = url + ("&position={}%3A{}-{}&pix={}".format(view["chromosome"],(view["start"]-margins),(view["finish"]+margins),pixels))
        file_loc = "{}/tn{}.png".format(folder,view['id'])
        try:
            urlretrieve(to_get,file_loc)
        except Exception as e:
            #try once more
            try:
                urlretrieve(to_get,file_loc)
            except Exception as e:
                failiures+=1
                if failiures>4:
                    if job:
                        job.outputs=dict(self.job.outputs)
                        job.outputs["uploaded_images"]=count-1
                        db.session.commit()
                        
                    raise Exception("too many errors") from e
                
        if count%25 == 0:
            msg = "{}/{} images".format(count,len(views))
            print (msg)
            if job:
                if job.status=="failed":
                    job.outputs=dict(job.outputs)
                    job.outputs["uploaded_images"]=count
                    db.session.commit()
                    break
                job.status=msg
                db.session.commit()
               
            
        time.sleep(delay)          
            
      
        